"""
Tests for the review workflow state machine: approve, reject, edit, and
the guard that refuses scheduling anything unapproved. These are the
"scary cases" the brief specifically calls out — a blocked variant, a
refused schedule — as a formal, automatically-discoverable pytest suite.
"""


def _create_draft_variants(client):
    resp = client.post(
        "/posts",
        json={"source_type": "markdown", "source_content": "# Foxes\n\nFoxes are clever."},
    )
    post_id = resp.json()["id"]
    resp = client.post(f"/posts/{post_id}/variants/generate")
    return resp.json()["created"]


def test_approve_draft_variant_succeeds(client):
    variant_id = _create_draft_variants(client)[0]["id"]

    resp = client.post(f"/variants/{variant_id}/approve")

    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_approving_twice_is_refused(client):
    variant_id = _create_draft_variants(client)[0]["id"]
    client.post(f"/variants/{variant_id}/approve")

    resp = client.post(f"/variants/{variant_id}/approve")

    assert resp.status_code == 409
    assert "only draft variants can be approved" in resp.json()["detail"]


def test_reject_blank_reason_is_rejected(client):
    variant_id = _create_draft_variants(client)[0]["id"]

    resp = client.post(f"/variants/{variant_id}/reject", json={"reason": ""})

    assert resp.status_code == 422


def test_reject_then_edit_resets_to_draft(client):
    variant_id = _create_draft_variants(client)[0]["id"]
    client.post(f"/variants/{variant_id}/reject", json={"reason": "needs work"})

    resp = client.patch(f"/variants/{variant_id}", json={"content": "Better content here."})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "draft"
    assert body["rejection_reason"] is None


def test_editing_an_approved_variant_is_refused(client):
    variant_id = _create_draft_variants(client)[0]["id"]
    client.post(f"/variants/{variant_id}/approve")

    resp = client.patch(f"/variants/{variant_id}", json={"content": "Trying to sneak an edit in."})

    assert resp.status_code == 409


def test_editing_with_a_constraint_violation_is_blocked(client):
    variant_id = next(
        v["id"] for v in _create_draft_variants(client) if v["platform"] == "x"
    )

    resp = client.patch(
        f"/variants/{variant_id}",
        json={"content": "#a #b #c #d #e #f"},  # 6 hashtags, X's limit is 2
    )

    assert resp.status_code == 422
    assert "Too many hashtags" in resp.json()["detail"]["violations"][0]


def test_scheduling_an_unapproved_variant_is_refused(client):
    """THE core requirement from the brief: an unapproved variant can
    never be scheduled, full stop."""
    variant_id = _create_draft_variants(client)[0]["id"]  # still draft

    resp = client.post(
        f"/variants/{variant_id}/schedule",
        json={"scheduled_at": "2027-01-01T00:00:00Z"},
    )

    assert resp.status_code == 409
    assert "only approved variants can be scheduled" in resp.json()["detail"]


def test_scheduling_an_approved_variant_succeeds(client):
    variant_id = _create_draft_variants(client)[0]["id"]
    client.post(f"/variants/{variant_id}/approve")

    resp = client.post(
        f"/variants/{variant_id}/schedule",
        json={"scheduled_at": "2027-01-01T00:00:00Z"},
    )

    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"


def test_review_actions_on_nonexistent_variant_return_404(client):
    import uuid

    resp = client.post(f"/variants/{uuid.uuid4()}/approve")

    assert resp.status_code == 404