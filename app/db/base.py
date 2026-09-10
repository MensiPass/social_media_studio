"""
Every model (Post, Variant, ScheduleSlot, PublishAttempt) inherits from this
one Base class. SQLAlchemy uses it to track all your table definitions in
one place, which is what lets Alembic auto-detect your schema.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass