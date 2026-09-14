"""
Unit test for TelegramPublisher's error-handling logic, using mocked HTTP
responses — no real network call, no real bot token needed. This runs
identically anywhere, including CI. For the actual live send to your real
Telegram chat, see scripts/smoke_test_telegram_live.py instead.

Run with:
    python scripts/smoke_test_telegram_unit.py
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.adapters.telegram_adapter import TelegramPublisher


def main() -> None:
    print("1) Missing bot_token/chat_id -> graceful failure, no network call attempted...")
    publisher = TelegramPublisher(bot_token="", chat_id="")
    result = publisher.publish("test message")
    assert result.success is False
    assert "not configured" in result.detail
    print(f"    {result.detail}\n")

    print("2) Simulated network error (e.g. no internet, DNS failure)...")
    publisher = TelegramPublisher(bot_token="fake-token", chat_id="12345")
    with patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")):
        result = publisher.publish("test message")
    assert result.success is False
    assert "Network error" in result.detail
    print(f"    {result.detail}\n")

    print("3) Simulated Telegram API rejection (e.g. bad token, bad chat_id)...")
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "ok": False,
        "description": "Unauthorized",
    }
    with patch("httpx.post", return_value=fake_response):
        result = publisher.publish("test message")
    assert result.success is False
    assert "Telegram API rejected" in result.detail
    assert "Unauthorized" in result.detail
    print(f"    {result.detail}\n")

    print("4) Simulated SUCCESSFUL send...")
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "ok": True,
        "result": {"message_id": 42},
    }
    with patch("httpx.post", return_value=fake_response):
        result = publisher.publish("test message")
    assert result.success is True
    assert result.external_post_id == "42"
    print(f"    {result.detail}\n")

    print("SMOKE TEST PASSED — Telegram adapter error handling works correctly.")
    print("NOTE: this test never made a real network call. Run")
    print("scripts/smoke_test_telegram_live.py to test against your real bot.")


if __name__ == "__main__":
    main()