"""
Smoke test for the POST /posts and GET /posts endpoints.

Uses an in-memory SQLite database via FastAPI's dependency override system —
this tests the ROUTE LOGIC itself (validation, status codes, response shape)
independent of whether Postgres is running. It does NOT replace testing
against real Postgres; it's a fast sanity check you can run anytime.

Run with:
    python scripts/smoke_test_api.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db

# --- Swap in a throwaway SQLite DB just for this test run ---
# StaticPool forces SQLAlchemy to reuse ONE connection for this in-memory
# database. Without it, each new connection gets its own empty :memory:
# database (a SQLite-specific quirk), which would make our tables
# "disappear" between the create_all() call and the actual test requests.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def main() -> None:
    print("1) Creating a post from pasted Markdown...")
    resp = client.post(
        "/posts",
        json={
            "source_type": "markdown",
            "source_content": "# Red Foxes\n\nFoxes are clever, adaptable animals found worldwide.",
        },
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    post = resp.json()
    assert post["title"] == "Red Foxes", f"Expected title 'Red Foxes', got {post['title']!r}"
    print(f" Created post {post['id']} — title parsed correctly: {post['title']!r}\n")

    print("2) Fetching that post back by ID...")
    resp = client.get(f"/posts/{post['id']}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print(" Post retrieved correctly.\n")

    print("3) Listing all posts...")
    resp = client.get("/posts")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    print(f"List endpoint returned {len(resp.json())} post(s).\n")

    print("4) Submitting a blank Markdown post (should be rejected)...")
    resp = client.post("/posts", json={"source_type": "markdown", "source_content": "   "})
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
    print(f" Correctly rejected with {resp.status_code}.\n")

    print("5) Requesting a post that doesn't exist (should 404)...")
    import uuid
    resp = client.get(f"/posts/{uuid.uuid4()}")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    print(f"Correctly returned {resp.status_code}.\n")

    print("6) Creating a post from a real URL (github.com)...")
    resp = client.post(
        "/posts",
        json={"source_type": "url", "source_content": "https://github.com/fastapi/fastapi"},
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    url_post = resp.json()
    assert len(url_post["source_content"]) > 100, "Expected real extracted article text"
    print(f"URL fetched and extracted — {len(url_post['source_content'])} chars of text stored.\n")

    print("SMOKE TEST PASSED — post ingestion works correctly.")


if __name__ == "__main__":
    main()