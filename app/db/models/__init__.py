"""
Importing every model here (even though nothing in this file "uses" them
directly) is what lets SQLAlchemy resolve relationships like Variant.post
correctly. Always import new models here as you add them.
"""
from app.db.models.post import Post
from app.db.models.variant import Variant, Platform, VariantStatus
from app.db.models.schedule_slot import ScheduleSlot, SlotStatus
from app.db.models.publish_attempt import PublishAttempt, AttemptStatus

__all__ = [
    "Post",
    "Variant",
    "Platform",
    "VariantStatus",
    "ScheduleSlot",
    "SlotStatus",
    "PublishAttempt",
    "AttemptStatus",
]
