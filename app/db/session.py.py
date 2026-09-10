"""
Sets up the actual connection to Postgres and hands out short-lived
"sessions" (a session = one conversation with the database for one request).

get_db() is a FastAPI dependency: FastAPI calls it before your route runs,
gives your route the session, and closes it automatically after — even if
the route raises an error. You'll see `db: Session = Depends(get_db)` in
every route starting Day 3.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()