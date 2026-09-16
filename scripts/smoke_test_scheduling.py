"""
Smoke test for the scheduling pipeline: a due, approved variant gets
claimed and actually published, without any real HTTP request or Celery
worker process running.

Uses Celery's task_always_eager mode so .delay() calls run synchronously
in-process — no real Redis broker needed for this test. Uses SQLite (via
monkeypatching app.db.session.SessionLocal) so no real Postgres is needed
either. This tests the LOGIC end-to-end; running the real `celery worker`
+ `celery beat` processes against real Redis/Postgres is the separate live
check in scripts/README notes below.

Run with:
    python scripts/smoke_test_scheduling.py
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

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
TestSessionLocal = sessionmaker(bind=engine)


def main() -> None:
    with patch("app.db.session.SessionLocal", TestSessionLocal):
        # Imported AFTER patching so the tasks module's module-qualified
        # db_session.SessionLocal() calls pick up the patched version.
        from app.core.celery_app import celery_app
        from app.tasks import publish_tasks

        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        db = TestSessionLocal()

        print("1) Creating an approved variant, scheduled 1 second in the past (already due)...")
        post = Post(source_type="markdown", source_content="# Foxes\n\nFoxes are clever.")
        variant = Variant(post=post, platform=Platform.X, content="Foxes are clever. #wildlife")
        variant.status = VariantStatus.APPROVED
        db.add(post)
        db.add(variant)
        db.commit()

        due_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        slot = ScheduleSlot(
            variant_id=variant.id,
            scheduled_at=due_time,
            idempotency_key=f"{variant.id}:{due_time.isoformat()}",
        )
        db.add(slot)
        db.commit()
        print(f"    Slot created, status={slot.status.value}\n")

        print("2) Running check_due_slots() (claims + dispatches due slots)...")
        claimed = publish_tasks.check_due_slots()
        assert claimed == 1, f"Expected 1 claimed, got {claimed}"
        print(f"    {claimed} slot claimed and dispatched\n")

        print("3) Verifying the slot was actually published (eager mode ran it synchronously)...")
        db.refresh(slot)
        db.refresh(variant)
        assert slot.status == SlotStatus.COMPLETED, f"Expected COMPLETED, got {slot.status}"
        assert variant.status == VariantStatus.PUBLISHED, f"Expected PUBLISHED, got {variant.status}"
        print(f"    Slot status: {slot.status.value}")
        print(f"    Variant status: {variant.status.value}\n")

        print("4) Verifying a PublishAttempt was recorded...")
        attempts = db.query(PublishAttempt).filter_by(schedule_slot_id=slot.id).all()
        assert len(attempts) == 1, f"Expected 1 attempt, got {len(attempts)}"
        attempt = attempts[0]
        print(f"    Attempt status: {attempt.status.value}")
        print(f"    External post ID: {attempt.external_post_id}")
        print(f"    Detail: {attempt.detail}\n")

        print("5) Running check_due_slots() AGAIN — the completed slot should NOT be reclaimed...")
        claimed_again = publish_tasks.check_due_slots()
        assert claimed_again == 0, f"Expected 0 claimed on second run, got {claimed_again}"
        print(f"    {claimed_again} slots claimed (correctly none — already completed)\n")

        print("6) Creating a FUTURE slot (not due yet) and confirming it's NOT claimed...")
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        future_slot = ScheduleSlot(
            variant_id=variant.id,
            scheduled_at=future_time,
            idempotency_key=f"{variant.id}:{future_time.isoformat()}",
        )
        db.add(future_slot)
        db.commit()
        claimed_future = publish_tasks.check_due_slots()
        assert claimed_future == 0, f"Expected 0 claimed (not due yet), got {claimed_future}"
        db.refresh(future_slot)
        assert future_slot.status == SlotStatus.PENDING
        print(f"    Future slot correctly left as PENDING, not claimed\n")

        db.close()

    print("SMOKE TEST PASSED — scheduling pipeline works correctly.")


if __name__ == "__main__":
    main()