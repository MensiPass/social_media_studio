"""
Scheduling endpoints:
  POST /variants/{variant_id}/schedule  -> create a ScheduleSlot for an approved variant
  GET  /schedule                        -> list all schedule slots
  GET  /schedule/{slot_id}              -> fetch one slot

Enforces review_workflow.ensure_schedulable — an unapproved variant can
never get a schedule slot, no matter what.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Variant, ScheduleSlot
from app.db.models.schedule_slot import SlotStatus
from app.services import review_workflow

router = APIRouter(tags=["schedule"])


class ScheduleCreate(BaseModel):
    scheduled_at: datetime


class ScheduleResponse(BaseModel):
    id: uuid.UUID
    variant_id: uuid.UUID
    scheduled_at: datetime
    status: SlotStatus
    idempotency_key: str

    model_config = {"from_attributes": True}


def _get_variant_or_404(variant_id: uuid.UUID, db: Session) -> Variant:
    variant = db.get(Variant, variant_id)
    if variant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Variant {variant_id} not found")
    return variant


@router.post(
    "/variants/{variant_id}/schedule",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def schedule_variant(
    variant_id: uuid.UUID, payload: ScheduleCreate, db: Session = Depends(get_db)
) -> ScheduleSlot:
    variant = _get_variant_or_404(variant_id, db)

    try:
        review_workflow.ensure_schedulable(variant)
    except review_workflow.InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    idempotency_key = f"{variant.id}:{payload.scheduled_at.isoformat()}"

    slot = ScheduleSlot(
        variant_id=variant.id,
        scheduled_at=payload.scheduled_at,
        idempotency_key=idempotency_key,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.get("/schedule", response_model=list[ScheduleResponse])
def list_schedule_slots(db: Session = Depends(get_db)) -> list[ScheduleSlot]:
    return db.query(ScheduleSlot).order_by(ScheduleSlot.scheduled_at).all()


@router.get("/schedule/{slot_id}", response_model=ScheduleResponse)
def get_schedule_slot(slot_id: uuid.UUID, db: Session = Depends(get_db)) -> ScheduleSlot:
    slot = db.get(ScheduleSlot, slot_id)
    if slot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Schedule slot {slot_id} not found")
    return slot