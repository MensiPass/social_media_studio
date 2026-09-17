"""
Smoke test for Day 10: idempotency guards + crash recovery.

Covers:
  1. Same publish call fired twice directly -> only ONE real publish happens
  2. A successful PublishAttempt already exists but slot status wasn't
     updated (the "crash between attempt-commit and status-commit" case)
     -> reconciled without re-publishing
  3. A slot stuck in PUBLISHING (simulating a worker that claimed it and
     then crashed) gets found and recovered by recover_stuck_slots
  4. Recovering an already-completed slot is a safe no-op (not reclaimed,
     not re-published)

Uses SQLite (monkeypatched) + Celery's task_always_eager mode, same
pattern as smoke_test_scheduling.py.

Run with:
    python scripts/smoke_test_idempotency.py
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Post, Variant, ScheduleSlot, PublishAttempt
from app.db.models.variant import Platform, VariantStatus
from app.db.models.schedule_slot import SlotStatus
from app.db.models.publish_attempt import AttemptStatus

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
TestSessionLocal = sessionmaker(bind=engine)


def make_approved_variant(db):
    post = Post(source_type="markdown", source_content="# Foxes\n\nFoxes are clever.")
    variant = Variant(post=post, platform=Platform.X, content="Foxes are clever. #wildlife")
    variant.status = VariantStatus.APPROVED
    db.add(post)
    db.add(variant)
    db.commit()
    return variant


def main() -> None:
    with patch("app.db.session.SessionLocal", TestSessionLocal):
        from app.core.celery_app import celery_app
        from app.tasks import publish_tasks
        from app.adapters.registry import get_publisher

        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        x_publisher = get_publisher(Platform.X)  # the shared MockXPublisher instance

        db = TestSessionLocal()

        # ============================================================
        print("1) Same publish_slot() call fired TWICE for the same slot...")
        variant = make_approved_variant(db)
        due_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        slot = ScheduleSlot(
            variant_id=variant.id,
            scheduled_at=due_time,
            idempotency_key=f"{variant.id}:{due_time.isoformat()}",
            status=SlotStatus.PUBLISHING,  # simulate already-claimed, ready to publish
        )
        db.add(slot)
        db.commit()

        sent_before = len(x_publisher.sent_posts)
        publish_tasks.publish_slot(str(slot.id))
        publish_tasks.publish_slot(str(slot.id))  # fired again — should be a no-op
        sent_after = len(x_publisher.sent_posts)

        actual_publishes = sent_after - sent_before
        assert actual_publishes == 1, f"Expected exactly 1 real publish, got {actual_publishes}"

        attempts = db.query(PublishAttempt).filter_by(schedule_slot_id=slot.id).all()
        assert len(attempts) == 1, f"Expected exactly 1 PublishAttempt row, got {len(attempts)}"
        print(f"    Called publish_slot() twice, but the adapter was only actually "
              f"called {actual_publishes} time — idempotency guard #1 worked.")
        print(f"    Exactly {len(attempts)} PublishAttempt row exists.\n")

        # ============================================================
        print("2) A successful attempt exists, but slot status is still PUBLISHING")
        print("   (simulating: crash happened AFTER recording success, BEFORE status update)...")
        variant2 = make_approved_variant(db)
        due_time2 = datetime.now(timezone.utc) - timedelta(seconds=1)
        slot2 = ScheduleSlot(
            variant_id=variant2.id,
            scheduled_at=due_time2,
            idempotency_key=f"{variant2.id}:{due_time2.isoformat()}",
            status=SlotStatus.PUBLISHING,
        )
        db.add(slot2)
        db.commit()

        # Manually insert the "already succeeded" attempt, WITHOUT going through
        # publish_slot — this simulates the narrow crash window directly.
        fake_attempt = PublishAttempt(
            schedule_slot_id=slot2.id,
            status=AttemptStatus.SUCCESS,
            external_post_id="mock-x-simulated-pre-crash",
            detail="[MOCK X] Simulated pre-crash success",
        )
        db.add(fake_attempt)
        db.commit()

        sent_before = len(x_publisher.sent_posts)
        publish_tasks.publish_slot(str(slot2.id))
        sent_after = len(x_publisher.sent_posts)

        assert sent_after == sent_before, "Should NOT have called the publisher again!"
        db.refresh(slot2)
        db.refresh(variant2)
        assert slot2.status == SlotStatus.COMPLETED
        assert variant2.status == VariantStatus.PUBLISHED
        print(f"    Publisher was NOT called again (idempotency guard #2 worked).")
        print(f"    Slot/variant status correctly reconciled to completed/published.\n")

        # ============================================================
        print("3) A slot stuck in PUBLISHING for longer than the threshold gets recovered...")
        variant3 = make_approved_variant(db)
        due_time3 = datetime.now(timezone.utc) - timedelta(minutes=10)
        stuck_slot = ScheduleSlot(
            variant_id=variant3.id,
            scheduled_at=due_time3,
            idempotency_key=f"{variant3.id}:{due_time3.isoformat()}",
            status=SlotStatus.PUBLISHING,
        )
        db.add(stuck_slot)
        db.commit()
        # Force updated_at to look like it was claimed 5 minutes ago —
        # well past the default 120-second stuck threshold.
        stuck_slot.updated_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.commit()

        sent_before = len(x_publisher.sent_posts)
        recovered_count = publish_tasks.recover_stuck_slots()
        sent_after = len(x_publisher.sent_posts)

        assert recovered_count == 1, f"Expected 1 stuck slot recovered, got {recovered_count}"
        assert sent_after - sent_before == 1, "Expected exactly 1 real publish from recovery"
        db.refresh(stuck_slot)
        assert stuck_slot.status == SlotStatus.COMPLETED
        print(f"    {recovered_count} stuck slot found and successfully recovered.")
        print(f"    Adapter was called exactly once — a real post happened, as it should.\n")

        # ============================================================
        print("4) Running recover_stuck_slots() AGAIN — the now-completed slot must NOT be reclaimed...")
        sent_before = len(x_publisher.sent_posts)
        recovered_again = publish_tasks.recover_stuck_slots()
        sent_after = len(x_publisher.sent_posts)

        assert recovered_again == 0, f"Expected 0 (already completed), got {recovered_again}"
        assert sent_after == sent_before, "Should NOT have published again!"
        print(f"    {recovered_again} slots recovered (correctly none — already completed).\n")

        db.close()

    print("SMOKE TEST PASSED — idempotency guards and crash recovery work correctly.")


if __name__ == "__main__":
    main()