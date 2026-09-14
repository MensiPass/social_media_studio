"""
LIVE Telegram test — actually sends a real message using your real
TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from .env. This is the genuine
"a real message lands in your own channel" proof required by the brief.

Only run this after completing the BotFather setup and filling in .env.

Run with:
    python scripts/smoke_test_telegram_live.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.adapters.telegram_adapter import TelegramPublisher


def main() -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        print(" TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing from your .env file.")
        print("   Follow the BotFather setup steps, then fill both values in .env, then retry.")
        sys.exit(1)

    print(f"Bot token starts with: {settings.telegram_bot_token[:10]}...")
    print(f"Chat ID: {settings.telegram_chat_id}")
    print("\nSending a real test message to your Telegram chat...\n")

    publisher = TelegramPublisher(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )
    result = publisher.publish(
        " Social Media Studio — Day 7 live test. If you can see this, "
        "your real Telegram adapter is working correctly."
    )

    if result.success:
        print(f" SUCCESS — message sent!")
        print(f"   External post ID (Telegram message_id): {result.external_post_id}")
        print(f"   Detail: {result.detail}")
        print("\nGo check your Telegram chat with the bot — the message should be there now.")
    else:
        print(f" FAILED: {result.detail}")
        print("\nCommon causes:")
        print("  - Bot token is wrong or has a typo")
        print("  - chat_id is wrong (must be the numeric ID from getUpdates, not the bot's username)")
        print("  - You haven't sent the bot a message yet (getUpdates returns nothing until you do)")
        sys.exit(1)


if __name__ == "__main__":
    main()