"""
Pydantic schemas for the Variant API — request/response shapes, separate
from the SQLAlchemy Variant model in app/db/models/variant.py.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models.variant import Platform, VariantStatus


class VariantCreate(BaseModel):
    """Manual variant creation — a human supplies the exact content."""

    platform: Platform
    content: str = Field(min_length=1, max_length=200_000)


class VariantResponse(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    platform: Platform
    content: str
    status: VariantStatus
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BlockedVariant(BaseModel):
    """Reported (never stored) when a generated variant fails validation."""

    platform: Platform
    reasons: list[str]


class GenerateVariantsResponse(BaseModel):
    created: list[VariantResponse]
    blocked: list[BlockedVariant]