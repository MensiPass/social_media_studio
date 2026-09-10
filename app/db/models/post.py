"""
A Post is the one stored copy of the original blog content. Everything else
(variants) is generated FROM this and must trace back to it — this is the
"source of truth" principle from the brief.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.variant import Variant


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # "url" or "markdown" — tells us how source_content should be interpreted
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Either the URL we fetched from, or the raw Markdown text pasted in
    source_content: Mapped[str] = mapped_column(Text, nullable=False)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # One post can have many variants (one per platform).
    # cascade="all, delete-orphan" means: delete the post -> its variants go too.
    variants: Mapped[list["Variant"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )