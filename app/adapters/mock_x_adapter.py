"""
Records what WOULD be posted to X, without calling any real API — real X
posting access requires paid developer approval, so this stands in for it
per the brief's requirement for mock adapters on platforms we can't
actually reach.
"""
import uuid
from datetime import datetime, timezone

from app.adapters.base import SocialPublisher, PublishResult


class MockXPublisher(SocialPublisher):
    """
    Keeps an in-memory record of everything "published" through it, so
    tests can show what a real X adapter would have sent. This list resets
    on process restart — durable persistence lives in the publish_attempts
    table, wired up in Day 9 regardless of which adapter is used.
    """

    def __init__(self) -> None:
        self.sent_posts: list[dict] = []

    def publish(self, content: str) -> PublishResult:
        fake_id = f"mock-x-{uuid.uuid4().hex[:10]}"
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
            detail=f"[MOCK X] Would post: {preview}",
        )