"""
A Variant is one platform-specific rewrite of a Post — the LinkedIn version,
the X version, etc. Its `status` field drives the whole review workflow:
draft -> approved/rejected -> published. Only APPROVED variants may ever
be scheduled (enforced in Day 5's API, not just here).
"""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, ForeignKey, Uuid, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.post import Post
    from app.db.models.schedule_slot import ScheduleSlot


class Platform(str, enum.Enum):
    X = "x"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    TELEGRAM = "telegram"


class VariantStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class Variant(Base):
    __tablename__ = "variants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("posts.id"), nullable=False
    )

    platform: Mapped[Platform] = mapped_column(
        SAEnum(Platform, name="platform_enum"), nullable=False
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[VariantStatus] = mapped_column(
        SAEnum(VariantStatus, name="variant_status_enum"),
        default=VariantStatus.DRAFT,
        nullable=False,
    )

    # Filled in when a constraint-profile rule blocks this variant,
    # or when a human rejects it in the review workflow.
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    post: Mapped["Post"] = relationship(back_populates="variants")
    schedule_slots: Mapped[list["ScheduleSlot"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )