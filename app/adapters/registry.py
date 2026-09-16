"""
Maps each Platform to the publisher implementation currently configured
for it. This is the ONE place platform -> adapter wiring lives — swap an
adapter by changing this mapping, never by touching business logic that
calls .publish().

Real adapters (Telegram, LinkedIn) are added here on Day 7 and Day 8.
Until then, requesting one of those platforms raises a clear error rather
than silently doing nothing.
"""
from app.db.models.variant import Platform
from app.core.config import settings
from app.adapters.base import SocialPublisher
from app.adapters.mock_x_adapter import MockXPublisher
from app.adapters.mock_instagram_adapter import MockInstagramPublisher
from app.adapters.telegram_adapter import TelegramPublisher
from app.adapters.linkedin_adapter import LinkedInPublisher

_REGISTRY: dict[Platform, SocialPublisher] = {
    Platform.X: MockXPublisher(),
    Platform.INSTAGRAM: MockInstagramPublisher(),
    Platform.TELEGRAM: TelegramPublisher(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    ),
    Platform.LINKEDIN: LinkedInPublisher(
        access_token=settings.linkedin_access_token,
        person_urn=settings.linkedin_person_urn,
        api_version=settings.linkedin_api_version,
    ),
}


def get_publisher(platform: Platform) -> SocialPublisher:
    try:
        return _REGISTRY[platform]
    except KeyError as exc:
        raise NotImplementedError(
            f"No publisher configured yet for platform '{platform.value}'. "
            f"(Telegram and LinkedIn adapters are added on Day 7-8.)"
        ) from exc