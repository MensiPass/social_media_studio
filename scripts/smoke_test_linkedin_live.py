"""
LIVE LinkedIn test — actually posts using your real LINKEDIN_ACCESS_TOKEN
and LINKEDIN_PERSON_URN from .env. This is the genuine "a real post lands
on your LinkedIn profile" proof required by the brief.

Only run this AFTER completing the OAuth flow (visit /oauth/linkedin/login
in your browser while the server is running) and filling in .env.

Run with:
    python scripts/smoke_test_linkedin_live.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.adapters.linkedin_adapter import LinkedInPublisher


def main() -> None:
    if not settings.linkedin_access_token or not settings.linkedin_person_urn:
        print(" LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN is missing from .env.")
        print("   1. Run: uvicorn app.main:app --reload")
        print("   2. Visit http://localhost:8000/oauth/linkedin/login in your browser")
        print("   3. Approve the LinkedIn consent screen")
        print("   4. Copy the two values shown into your .env file")
        print("   5. Re-run this script")
        sys.exit(1)

    print(f"Access token starts with: {settings.linkedin_access_token[:15]}...")
    print(f"Person URN: {settings.linkedin_person_urn}")
    print(f"API version: {settings.linkedin_api_version}")
    print("\nSending a real test post to your LinkedIn profile...\n")

    publisher = LinkedInPublisher(
        access_token=settings.linkedin_access_token,
        person_urn=settings.linkedin_person_urn,
        api_version=settings.linkedin_api_version,
    )
    result = publisher.publish(
        "Testing my Social Media Studio capstone project — Day 8 live LinkedIn "
        "integration. If you're seeing this, the real adapter works. "
    )

    if result.success:
        print(f" SUCCESS — post published!")
        print(f"   External post ID (LinkedIn URN): {result.external_post_id}")
        print(f"   Detail: {result.detail}")
        print("\nGo check your LinkedIn profile feed — the post should be there now.")
    else:
        print(f" FAILED: {result.detail}")
        print("\nCommon causes:")
        print("  - Access token expired (they last ~60 days) — redo the OAuth flow")
        print("  - LINKEDIN_API_VERSION is stale — check current value at:")
        print("    https://learn.microsoft.com/en-us/linkedin/marketing/versioning")
        print("  - person_urn is malformed — should look like 'urn:li:person:AbCdEfGhIj'")
        sys.exit(1)


if __name__ == "__main__":
    main()