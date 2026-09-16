"""
Real LinkedIn adapter. Publishes via LinkedIn's current Posts API
(POST /rest/posts). Requires an access token + person URN obtained once
via the OAuth flow in app/api/routes/oauth.py and stored in .env.
"""
import httpx

from app.adapters.base import SocialPublisher, PublishResult

LINKEDIN_API_BASE = "https://api.linkedin.com"


class LinkedInPublisher(SocialPublisher):
    def __init__(
        self,
        access_token: str,
        person_urn: str,
        api_version: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._access_token = access_token
        self._person_urn = person_urn
        self._api_version = api_version
        self._timeout = timeout_seconds

    def publish(self, content: str) -> PublishResult:
        if not self._access_token or not self._person_urn:
            return PublishResult(
                success=False,
                external_post_id=None,
                detail=(
                    "LinkedIn not configured: LINKEDIN_ACCESS_TOKEN or "
                    "LINKEDIN_PERSON_URN is missing from .env. "
                    "Run the OAuth flow at /oauth/linkedin/login first."
                ),
            )

        url = f"{LINKEDIN_API_BASE}/rest/posts"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": self._api_version,
            "Content-Type": "application/json",
        }
        body = {
            "author": self._person_urn,
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED"},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        try:
            response = httpx.post(url, json=body, headers=headers, timeout=self._timeout)
        except httpx.RequestError as exc:
            return PublishResult(
                success=False,
                external_post_id=None,
                detail=f"Network error contacting LinkedIn: {exc}",
            )

        if response.status_code not in (200, 201):
            return PublishResult(
                success=False,
                external_post_id=None,
                detail=(
                    f"LinkedIn API rejected the post (HTTP {response.status_code}): "
                    f"{response.text[:300]}"
                ),
            )

        # LinkedIn's Posts API returns the new post's URN in the
        # 'x-restli-id' response header (Rest.li convention), not the body.
        post_urn = response.headers.get("x-restli-id")
        if not post_urn:
            try:
                post_urn = response.json().get("id", "unknown")
            except ValueError:
                post_urn = "unknown"

        return PublishResult(
            success=True,
            external_post_id=post_urn,
            detail=f"Posted to LinkedIn, post URN={post_urn}",
        )