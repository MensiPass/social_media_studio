"""
Unit test for LinkedInPublisher's error-handling logic, using mocked HTTP
responses — no real network call, no real credentials needed. For the
actual live send + OAuth flow, see scripts/smoke_test_linkedin_live.py.

Run with:
    python scripts/smoke_test_linkedin_unit.py
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.adapters.linkedin_adapter import LinkedInPublisher


def main() -> None:
    print("1) Missing access_token/person_urn -> graceful failure, no network call...")
    publisher = LinkedInPublisher(access_token="", person_urn="", api_version="202606")
    result = publisher.publish("test post")
    assert result.success is False
    assert "not configured" in result.detail
    print(f"    {result.detail}\n")

    publisher = LinkedInPublisher(
        access_token="fake-token", person_urn="urn:li:person:abc123", api_version="202606"
    )

    print("2) Simulated network error...")
    with patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")):
        result = publisher.publish("test post")
    assert result.success is False
    assert "Network error" in result.detail
    print(f"    {result.detail}\n")

    print("3) Simulated LinkedIn API rejection (e.g. expired token -> 401)...")
    fake_response = MagicMock()
    fake_response.status_code = 401
    fake_response.text = '{"message": "Invalid access token"}'
    with patch("httpx.post", return_value=fake_response):
        result = publisher.publish("test post")
    assert result.success is False
    assert "HTTP 401" in result.detail
    print(f"    {result.detail}\n")

    print("4) Simulated SUCCESSFUL post (URN in response header, LinkedIn's actual convention)...")
    fake_response = MagicMock()
    fake_response.status_code = 201
    fake_response.headers = {"x-restli-id": "urn:li:share:1234567890"}
    with patch("httpx.post", return_value=fake_response):
        result = publisher.publish("test post")
    assert result.success is True
    assert result.external_post_id == "urn:li:share:1234567890"
    print(f"    {result.detail}\n")

    print("SMOKE TEST PASSED — LinkedIn adapter error handling works correctly.")
    print("NOTE: this test never made a real network call. Run")
    print("scripts/smoke_test_linkedin_live.py to test against your real LinkedIn account.")


if __name__ == "__main__":
    main()