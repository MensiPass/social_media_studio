"""
Celery tasks: the actual background work that publishes approved,
scheduled variants without any HTTP request being involved.

check_due_slots runs on Celery Beat's schedule (every 30s, see
celery_app.py) and looks for PENDING slots whose time has come. It does
NOT publish anything itself — it CLAIMS due slots (PENDING -> PUBLISHING)
and hands each one off to publish_slot as a separate task. Claiming a slot
before dispatching it is what prevents the same slot being enqueued twice
if a Beat tick overlaps with a slow worker.

publish_slot does the actual work for ONE slot: call the right adapter,
record a PublishAttempt, and update the slot + variant status. It has TWO
idempotency guards (added Day 10) so calling it twice for the same slot —
whether from a retry, a duplicate message, or crash-recovery re-dispatch —
never results in a duplicate real-world post. See each guard's comment
below for exactly what it catches.

recover_stuck_slots (added Day 10) finds slots claimed (PUBLISHING) longer
than settings.stuck_slot_threshold_seconds without finishing — the
signature of a worker that claimed a slot and then crashed — and
re-dispatches them. This is safe specifically BECAUSE of publish_slot's
idempotency guards: re-dispatching a slot that actually already finished
is a harmless no-op, not a duplicate post.

Note: these use `db_session.SessionLocal()` (module-qualified) rather than
`from app.db.session import SessionLocal` directly — this makes the
functions testable, since tests can monkeypatch
app.db.session.SessionLocal and have it actually take effect here.
"""
import uuid
from datetime import datetime, timedelta, timezone

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db import session as db_session
from app.db.models import ScheduleSlot, Variant, PublishAttempt
from app.db.models.schedule_slot import SlotStatus
from app.db.models.variant import VariantStatus
from app.db.models.publish_attempt import AttemptStatus
from app.adapters.registry import get_publisher


@celery_app.task(name="app.tasks.publish_tasks.check_due_slots")
def check_due_slots() -> int:
    """
    Finds PENDING slots whose scheduled_at has passed, claims them
    (PENDING -> PUBLISHING), and enqueues publish_slot for each.
    Returns the number of slots claimed (useful for logging/tests).
    """
    db = db_session.SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_slots = (
            db.query(ScheduleSlot)
            .filter(ScheduleSlot.status == SlotStatus.PENDING)
            .filter(ScheduleSlot.scheduled_at <= now)
            .all()
        )
        for slot in due_slots:
            slot.status = SlotStatus.PUBLISHING
        db.commit()

        slot_ids = [str(slot.id) for slot in due_slots]

        # Enqueue AFTER commit, so a slot is never left claimed in the DB
        # without a task actually dispatched for it.
        for slot_id in slot_ids:
            publish_slot.delay(slot_id)

        return len(slot_ids)
    finally:
        db.close()


@celery_app.task(name="app.tasks.publish_tasks.recover_stuck_slots")
def recover_stuck_slots() -> int:
    """
    Finds slots stuck in PUBLISHING for longer than
    settings.stuck_slot_threshold_seconds and re-dispatches them. This is
    what makes crash recovery actually happen — without it, a slot claimed
    by a worker that then died would stay PUBLISHING forever, since
    check_due_slots only ever looks at PENDING slots.
    """
    db = db_session.SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.stuck_slot_threshold_seconds
        )
        stuck_slots = (
            db.query(ScheduleSlot)
            .filter(ScheduleSlot.status == SlotStatus.PUBLISHING)
            .filter(ScheduleSlot.updated_at <= cutoff)
            .all()
        )
        slot_ids = [str(slot.id) for slot in stuck_slots]
    finally:
        db.close()

    for slot_id in slot_ids:
        publish_slot.delay(slot_id)

    return len(slot_ids)


@celery_app.task(name="app.tasks.publish_tasks.publish_slot")
def publish_slot(slot_id: str) -> None:
    db = db_session.SessionLocal()
    try:
        slot = db.get(ScheduleSlot, uuid.UUID(slot_id))
        if slot is None:
            return  # slot was deleted; nothing to do

        # --- Idempotency guard #1: already fully completed ---
        # Covers the common case: this exact task ran to completion once
        # already, and got called again anyway (retry, duplicate message,
        # a stale recover_stuck_slots re-dispatch after it actually
        # finished). Nothing to do — the work is done.
        if slot.status == SlotStatus.COMPLETED:
            return

        # --- Idempotency guard #2: a successful attempt already exists ---
        # Covers a narrower case: the slot's status update didn't make it
        # to COMPLETED (e.g. a crash between recording the attempt and
        # updating slot/variant status), but the PublishAttempt row proving
        # the real post succeeded DID get committed. We must NOT call the
        # publisher again — we just reconcile the status to match reality.
        existing_success = (
            db.query(PublishAttempt)
            .filter(PublishAttempt.schedule_slot_id == slot.id)
            .filter(PublishAttempt.status == AttemptStatus.SUCCESS)
            .first()
        )
        if existing_success is not None:
            slot.status = SlotStatus.COMPLETED
            variant = db.get(Variant, slot.variant_id)
            variant.status = VariantStatus.PUBLISHED
            db.commit()
            return

        variant = db.get(Variant, slot.variant_id)
        publisher = get_publisher(variant.platform)
        result = publisher.publish(variant.content)

        attempt = PublishAttempt(
            schedule_slot_id=slot.id,
            status=AttemptStatus.SUCCESS if result.success else AttemptStatus.FAILURE,
            external_post_id=result.external_post_id,
            detail=result.detail,
        )
        db.add(attempt)

        if result.success:
            slot.status = SlotStatus.COMPLETED
            variant.status = VariantStatus.PUBLISHED
        else:
            slot.status = SlotStatus.FAILED

        db.commit()
    finally:
        db.close()