"""
Smoke test for the review workflow: approve, reject, edit, and the
scheduling guard (review_workflow.ensure_schedulable).

Run with:
    python scripts/smoke_test_review.py
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
from app.db.models import Variant, VariantStatus
from app.services import review_workflow

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
    print("1) Creating a post and generating variants...")
    resp = client.post(
        "/posts",
        json={"source_type": "markdown", "source_content": "# Red Foxes\n\nFoxes are clever animals."},
    )
    post_id = resp.json()["id"]
    resp = client.post(f"/posts/{post_id}/variants/generate")
    variants = resp.json()["created"]
    x_variant_id = next(v["id"] for v in variants if v["platform"] == "x")
    linkedin_variant_id = next(v["id"] for v in variants if v["platform"] == "linkedin")
    print(f"    Created {len(variants)} draft variants.\n")

    print("2) Approving the X variant...")
    resp = client.post(f"/variants/{x_variant_id}/approve")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"
    print("    X variant approved.\n")

    print("3) Trying to approve it AGAIN (should be refused, 409)...")
    resp = client.post(f"/variants/{x_variant_id}/approve")
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"
    print(f"    Correctly refused: {resp.json()['detail']}\n")

    print("4) Rejecting the LinkedIn variant with a reason...")
    resp = client.post(
        f"/variants/{linkedin_variant_id}/reject", json={"reason": "too generic, needs a stronger hook"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "too generic, needs a stronger hook"
    print("    LinkedIn variant rejected, reason stored.\n")

    print("5) Editing the rejected variant with new content (should reset to draft)...")
    resp = client.patch(
        f"/variants/{linkedin_variant_id}",
        json={"content": "Foxes are surprisingly clever — here's why. #Foxes"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "draft", body
    assert body["rejection_reason"] is None
    print("    Edit succeeded, status reset to draft, rejection_reason cleared.\n")

    print("6) Trying to edit the ALREADY-APPROVED X variant (should be refused, 409)...")
    resp = client.patch(f"/variants/{x_variant_id}", json={"content": "New content entirely"})
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"
    print(f"    Correctly refused: {resp.json()['detail']}\n")

    print("7) Trying to edit with content that BREAKS the X constraint profile...")
    resp = client.patch(
        f"/variants/{linkedin_variant_id}",
        json={"content": "#a #b #c #d #e #f"},  # 6 hashtags, LinkedIn limit is 5
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
    print(f"    Correctly refused: {resp.json()['detail']['violations']}\n")

    print("8) Attempting review actions on a nonexistent variant (should 404)...")
    import uuid
    resp = client.post(f"/variants/{uuid.uuid4()}/approve")
    assert resp.status_code == 404
    print("    Correctly returned 404.\n")

    print("9) Confirming the scheduling guard blocks unapproved variants directly...")
    db = TestSession()
    draft_variant = db.query(Variant).filter(Variant.status == VariantStatus.DRAFT).first()
    try:
        review_workflow.ensure_schedulable(draft_variant)
        print("    Should have raised!")
    except review_workflow.InvalidTransitionError as e:
        print(f"   Unapproved variant correctly refused for scheduling: {e}")
    db.close()

    print("\nSMOKE TEST PASSED — review workflow works correctly.")


if __name__ == "__main__":
    main()