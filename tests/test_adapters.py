"""
Tests for the SocialPublisher interface, the adapter registry, and the
idempotency + crash-recovery guards in publish_slot. No real network calls
anywhere here — Telegram/LinkedIn live-network testing lives in the
separate scripts/*_live.py scripts, deliberately kept out of the automated
suite so `pytest` never sends a real message or post.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.base import SocialPublisher
from app.adapters.mock_x_adapter import MockXPublisher
from app.adapters import registry
from app.db.base import Base
from app.db.models import Post, Variant, ScheduleSlot, PublishAttempt
from app.db.models.variant import Platform, VariantStatus
from app.db.models.schedule_slot import SlotStatus


# ---------------------------------------------------------------------
# Interface + registry
# ---------------------------------------------------------------------

def test_social_publisher_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        SocialPublisher()


def test_mock_x_publisher_returns_success_and_records_post():
    publisher = MockXPublisher()

    result = publisher.publish("Test content")

    assert result.success is True
    assert result.external_post_id.startswith("mock-x-")
    assert len(publisher.sent_posts) == 1


def test_registry_swap_same_calling_code_different_platforms():
    """The adapter-swap requirement: identical calling code, different
    platforms, correctly routed — no if/else on platform anywhere here."""
    x_result = registry.get_publisher(Platform.X).publish("test")
    ig_result = registry.get_publisher(Platform.INSTAGRAM).publish("test")

    assert x_result.success and ig_result.success
    assert x_result.external_post_id.startswith("mock-x-")
    assert ig_result.external_post_id.startswith("mock-ig-")


def test_registry_returns_real_telegram_and_linkedin_instances():
    from app.adapters.telegram_adapter import TelegramPublisher
    from app.adapters.linkedin_adapter import LinkedInPublisher

    assert isinstance(registry.get_publisher(Platform.TELEGRAM), TelegramPublisher)
    assert isinstance(registry.get_publisher(Platform.LINKEDIN), LinkedInPublisher)


# ---------------------------------------------------------------------
# Idempotency + crash recovery
# (self-contained fixture: needs to patch app.db.session.SessionLocal AND
# enable Celery eager mode, which is more than the shared `client`/`db`
# fixtures in conftest.py provide)
# ---------------------------------------------------------------------

@pytest.fixture()
def task_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)

    with patch("app.db.session.SessionLocal", TestSessionLocal):
        from app.core.celery_app import celery_app

        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        session = TestSessionLocal()
        yield session
        session.close()


def _make_approved_variant(db):
    post = Post(source_type="markdown", source_content="# Foxes\n\nFoxes are clever.")
    variant = Variant(post=post, platform=Platform.X, content="Foxes are clever. #wildlife")
    variant.status = VariantStatus.APPROVED
    db.add(post)
    db.add(variant)
    db.commit()
    return variant


def test_duplicate_publish_call_creates_only_one_attempt(task_db):
    """THE scary case: same publish call fired twice -> one post, not two."""
    from app.tasks import publish_tasks

    x_publisher = registry.get_publisher(Platform.X)
    variant = _make_approved_variant(task_db)
    due = datetime.now(timezone.utc) - timedelta(seconds=1)
    slot = ScheduleSlot(
        variant_id=variant.id,
        scheduled_at=due,
        idempotency_key=f"{variant.id}:{due.isoformat()}",
        status=SlotStatus.PUBLISHING,
    )
    task_db.add(slot)
    task_db.commit()

    sent_before = len(x_publisher.sent_posts)
    publish_tasks.publish_slot(str(slot.id))
    publish_tasks.publish_slot(str(slot.id))  # the duplicate call
    sent_after = len(x_publisher.sent_posts)

    assert sent_after - sent_before == 1
    attempts = task_db.query(PublishAttempt).filter_by(schedule_slot_id=slot.id).all()
    assert len(attempts) == 1


def test_stuck_slot_is_recovered_and_completes(task_db):
    """A worker that claimed a slot and crashed before finishing — the
    slot must not be stuck forever."""
    from app.tasks import publish_tasks

    variant = _make_approved_variant(task_db)
    due = datetime.now(timezone.utc) - timedelta(minutes=10)
    slot = ScheduleSlot(
        variant_id=variant.id,
        scheduled_at=due,
        idempotency_key=f"{variant.id}:{due.isoformat()}",
        status=SlotStatus.PUBLISHING,
    )
    task_db.add(slot)
    task_db.commit()
    slot.updated_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    task_db.commit()

    recovered = publish_tasks.recover_stuck_slots()

    assert recovered == 1
    task_db.refresh(slot)
    assert slot.status == SlotStatus.COMPLETED


def test_completed_slot_is_never_reclaimed_by_recovery(task_db):
    from app.tasks import publish_tasks

    variant = _make_approved_variant(task_db)
    due = datetime.now(timezone.utc) - timedelta(minutes=10)
    slot = ScheduleSlot(
        variant_id=variant.id,
        scheduled_at=due,
        idempotency_key=f"{variant.id}:{due.isoformat()}",
        status=SlotStatus.COMPLETED,
    )
    task_db.add(slot)
    task_db.commit()

    recovered = publish_tasks.recover_stuck_slots()

    assert recovered == 0