"""
Smoke test for variant generation + constraint profile enforcement.

Uses the same in-memory SQLite pattern as smoke_test_api.py — tests route
logic independent of whether Postgres is running.

Run with:
    python scripts/smoke_test_variants.py
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
    print("1) Creating a post to generate variants from...")
    resp = client.post(
        "/posts",
        json={
            "source_type": "markdown",
            "source_content": (
                "# The Secret Life of Red Foxes\n\n"
                "Red foxes are remarkably adaptable animals found across the entire "
                "Northern Hemisphere, thriving in forests, grasslands, mountains, "
                "and even cities. They are known for their cunning hunting strategies."
            ),
        },
    )
    assert resp.status_code == 201, resp.text
    post_id = resp.json()["id"]
    print(f" Post created: {post_id}\n")

    print("2) Auto-generating variants for all 4 platforms...")
    resp = client.post(f"/posts/{post_id}/variants/generate")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["created"]) == 4, f"Expected 4 created, got {len(body['created'])}: {body}"
    assert len(body["blocked"]) == 0, f"Expected 0 blocked, got: {body['blocked']}"
    print(f" All 4 platform variants generated and passed validation:")
    for v in body["created"]:
        print(f"      - {v['platform']}: {len(v['content'])} chars, status={v['status']}")
    print()

    print("3) Attempting to manually create a variant that BREAKS the X length rule...")
    oversized_content = "This tweet is way too long. " * 20  # ~580 chars, X limit is 280
    resp = client.post(
        f"/posts/{post_id}/variants",
        json={"platform": "x", "content": oversized_content},
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
    detail = resp.json()["detail"]
    assert "Exceeds x max length" in detail["violations"][0], detail
    print(f" Correctly blocked with 422. Reason: {detail['violations'][0]}\n")

    print("4) Attempting to manually create a variant that BREAKS the X hashtag rule...")
    too_many_hashtags = "Foxes! #fox #wildlife #nature #animals #cute"  # 5 hashtags, X limit is 2
    resp = client.post(
        f"/posts/{post_id}/variants",
        json={"platform": "x", "content": too_many_hashtags},
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
    detail = resp.json()["detail"]
    assert "Too many hashtags" in detail["violations"][0], detail
    print(f" Correctly blocked with 422. Reason: {detail['violations'][0]}\n")

    print("5) Creating a VALID manual variant (should succeed)...")
    resp = client.post(
        f"/posts/{post_id}/variants",
        json={"platform": "x", "content": "Foxes are clever animals. #wildlife"},
    )
    assert resp.status_code == 201, resp.text
    print(" Valid variant created successfully.\n")

    print("6) Listing all variants for this post...")
    resp = client.get(f"/posts/{post_id}/variants")
    assert resp.status_code == 200
    assert len(resp.json()) == 5, f"Expected 5 (4 generated + 1 manual), got {len(resp.json())}"
    print(f" List returned {len(resp.json())} variants.\n")

    print("7) Generating variants for a nonexistent post (should 404)...")
    import uuid
    resp = client.post(f"/posts/{uuid.uuid4()}/variants/generate")
    assert resp.status_code == 404
    print(f"Correctly returned 404.\n")

    print("SMOKE TEST PASSED — variant generation and constraint enforcement work correctly.")


if __name__ == "__main__":
    main()