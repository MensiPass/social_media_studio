"""
Real Telegram adapter. Publishes by calling Telegram's Bot API sendMessage
endpoint. This is one of the two REAL (non-mock) publish targets the brief
requires — the other is LinkedIn, added Day 8.
"""
import httpx

from app.adapters.base import SocialPublisher, PublishResult

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramPublisher(SocialPublisher):
    def __init__(self, bot_token: str, chat_id: str, timeout_seconds: float = 10.0) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._timeout = timeout_seconds

    def publish(self, content: str) -> PublishResult:
        if not self._bot_token or not self._chat_id:
            return PublishResult(
                success=False,
                external_post_id=None,
                detail=(
                    "Telegram not configured: TELEGRAM_BOT_TOKEN or "
                    "TELEGRAM_CHAT_ID is missing from .env"
                ),
            )

        url = f"{TELEGRAM_API_BASE}/bot{self._bot_token}/sendMessage"

        try:
            response = httpx.post(
                url,
                json={"chat_id": self._chat_id, "text": content},
                timeout=self._timeout,
            )
            data = response.json()
        except httpx.RequestError as exc:
            return PublishResult(
                success=False,
                external_post_id=None,
                detail=f"Network error contacting Telegram: {exc}",
            )

        if not data.get("ok"):
            error_desc = data.get("description", "Unknown Telegram API error")
            return PublishResult(
                success=False,
                external_post_id=None,
                detail=f"Telegram API rejected the message: {error_desc}",
            )

        message_id = data["result"]["message_id"]
        return PublishResult(
            success=True,
            external_post_id=str(message_id),
            detail=f"Posted to Telegram, message_id={message_id}",
        )