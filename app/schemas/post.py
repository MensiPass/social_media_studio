"""
Pydantic schemas define what the API accepts and returns — separate from
app/db/models/post.py, which defines what's stored in the database.

Why separate: a client should never be able to set fields like `id` or
`created_at` themselves (PostCreate excludes them). A response should never
leak internal-only fields either. This separation is what makes FastAPI's
automatic request validation and /docs page work correctly.
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    URL = "url"
    MARKDOWN = "markdown"


class PostCreate(BaseModel):
    """What a client sends us to create a post."""

    source_type: SourceType
    # Either a URL string or raw Markdown text, depending on source_type.
    source_content: str = Field(min_length=1, max_length=200_000)

    @field_validator("source_content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("source_content cannot be blank")
        return stripped


class PostResponse(BaseModel):
    """What we send back after a post is created or fetched."""

    id: uuid.UUID
    source_type: SourceType
    source_content: str
    title: str | None
    created_at: datetime

    # Allows Pydantic to read values directly off the SQLAlchemy Post object
    # (post.id, post.title, ...) instead of requiring a plain dict.
    model_config = {"from_attributes": True}