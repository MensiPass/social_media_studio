"""
Shared pytest fixtures. Every test gets a fresh, isolated in-memory SQLite
database and a TestClient wired to it — no test leaks state into another,
and none of this touches your real Postgres.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db


@pytest.fixture()
def db_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)
    yield TestSessionLocal
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session_factory):
    """A TestClient wired to a fresh, isolated SQLite DB for this one test."""

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def db(db_session_factory):
    """
    Direct DB session for tests that need to set up state the API alone
    can't reach (e.g. forcing a specific status to simulate a crash).
    Shares the same underlying SQLite DB as the `client` fixture within
    one test, since both come from the same db_session_factory.
    """
    session = db_session_factory()
    yield session
    session.close()