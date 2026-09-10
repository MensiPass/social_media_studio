"""
A ScheduleSlot says "publish this Variant at this time." The
idempotency_key is the single most important column in this whole project —
before publishing, the worker checks "have I already used this key?" and
if so, does nothing. The UniqueConstraint below makes the database itself
refuse a duplicate slot, as a second line of defense beyond application code.
"""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.variant import Variant
    from app.db.models.publish_attempt import PublishAttempt


class SlotStatus(str, enum.Enum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"
    __table_args__ = (
        UniqueConstraint("variant_id", "scheduled_at", name="uq_variant_slot"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("variants.id"), nullable=False
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    status: Mapped[SlotStatus] = mapped_column(
        SAEnum(SlotStatus, name="slot_status_enum"),
        default=SlotStatus.PENDING,
        nullable=False,
    )

    # Unique per slot. Built and assigned on Day 9-10 (e.g. from variant_id + scheduled_at).
    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    variant: Mapped["Variant"] = relationship(back_populates="schedule_slots")
    publish_attempts: Mapped[list["PublishAttempt"]] = relationship(
        back_populates="schedule_slot", cascade="all, delete-orphan"
    )