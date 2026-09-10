"""
A PublishAttempt is a log row created every time the worker TRIES to publish
a slot — whether it succeeds or fails. This is your visible "publish history"
from the brief. Nothing ever gets deleted from this table; it's a record,
not a working table.
"""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.schedule_slot import ScheduleSlot


class AttemptStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class PublishAttempt(Base):
    __tablename__ = "publish_attempts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    schedule_slot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("schedule_slots.id"), nullable=False
    )

    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    status: Mapped[AttemptStatus] = mapped_column(
        SAEnum(AttemptStatus, name="attempt_status_enum"), nullable=False
    )

    # The ID the real platform (Telegram/LinkedIn) gave back, if successful
    external_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Error message on failure, or a short confirmation note on success
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    schedule_slot: Mapped["ScheduleSlot"] = relationship(
        back_populates="publish_attempts"
    )