"""
Records what WOULD be posted to Instagram, without calling any real API —
Instagram's real posting API requires business verification, so this stands
in for it per the brief's mock-adapter requirement.
"""
import uuid
from datetime import datetime, timezone

from app.adapters.base import SocialPublisher, PublishResult


class MockInstagramPublisher(SocialPublisher):
    """Same purpose as MockXPublisher — see that file's docstring."""

    def __init__(self) -> None:
        self.sent_posts: list[dict] = []

    def publish(self, content: str) -> PublishResult:
        fake_id = f"mock-ig-{uuid.uuid4().hex[:10]}"
        self.sent_posts.append(
            {
                "external_post_id": fake_id,
                "content": content,
                "posted_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        preview = content[:80] + ("..." if len(content) > 80 else "")
        return PublishResult(
            success=True,
            external_post_id=fake_id,
            detail=f"[MOCK INSTAGRAM] Would post: {preview}",
        )