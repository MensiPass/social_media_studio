"""
Publish history endpoints — a visible, queryable record of every publish
attempt ever made, success or failure. This is the audit-trail requirement
from the brief: "each attempt is recorded and visible, with its result."

Joins PublishAttempt -> ScheduleSlot -> Variant so each entry is
self-contained (platform, when it was scheduled for, when it was actually
attempted) without the caller needing separate lookups.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import PublishAttempt, ScheduleSlot, Variant
from app.db.models.publish_attempt import AttemptStatus
from app.db.models.variant import Platform

router = APIRouter(tags=["history"])


class HistoryEntry(BaseModel):
    attempt_id: uuid.UUID
    schedule_slot_id: uuid.UUID
    variant_id: uuid.UUID
    platform: Platform
    status: AttemptStatus
    external_post_id: str | None
    detail: str | None
    attempted_at: datetime
    scheduled_at: datetime


def _to_entry(attempt: PublishAttempt, slot: ScheduleSlot, variant: Variant) -> HistoryEntry:
    return HistoryEntry(
        attempt_id=attempt.id,
        schedule_slot_id=slot.id,
        variant_id=variant.id,
        platform=variant.platform,
        status=attempt.status,
        external_post_id=attempt.external_post_id,
        detail=attempt.detail,
        attempted_at=attempt.attempted_at,
        scheduled_at=slot.scheduled_at,
    )


@router.get("/history", response_model=list[HistoryEntry])
def list_publish_history(db: Session = Depends(get_db)) -> list[HistoryEntry]:
    rows = (
        db.query(PublishAttempt, ScheduleSlot, Variant)
        .join(ScheduleSlot, PublishAttempt.schedule_slot_id == ScheduleSlot.id)
        .join(Variant, ScheduleSlot.variant_id == Variant.id)
        .order_by(PublishAttempt.attempted_at.desc())
        .all()
    )
    return [_to_entry(attempt, slot, variant) for attempt, slot, variant in rows]


@router.get("/schedule/{slot_id}/attempts", response_model=list[HistoryEntry])
def list_attempts_for_slot(slot_id: uuid.UUID, db: Session = Depends(get_db)) -> list[HistoryEntry]:
    slot = db.get(ScheduleSlot, slot_id)
    if slot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Schedule slot {slot_id} not found")
    variant = db.get(Variant, slot.variant_id)

    attempts = (
        db.query(PublishAttempt)
        .filter(PublishAttempt.schedule_slot_id == slot_id)
        .order_by(PublishAttempt.attempted_at.desc())
        .all()
    )
    return [_to_entry(a, slot, variant) for a in attempts]