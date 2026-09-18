"""
Maps each Platform to the publisher implementation currently configured
for it. This is the ONE place platform -> adapter wiring lives.

Unlike earlier versions of this file, the mapping itself now comes from
settings (.env), not a hardcoded Python dict — this is what makes "swap
the adapter in configuration, no code change outside the adapters" (an
explicit acceptance check for this project) actually true rather than
aspirational. To route the 'telegram' platform through the mock instead
of the real bot, someone changes ADAPTER_MAP_TELEGRAM=mock_x in .env —
nothing in this file, or anywhere else, needs to change.
"""
from app.db.models.variant import Platform
from app.core.config import settings
from app.adapters.base import SocialPublisher
from app.adapters.mock_x_adapter import MockXPublisher
from app.adapters.mock_instagram_adapter import MockInstagramPublisher
from app.adapters.telegram_adapter import TelegramPublisher
from app.adapters.linkedin_adapter import LinkedInPublisher

# Every adapter this project knows how to build, by name. Adding a new
# adapter later means adding one line here — nothing else changes.
_ADAPTER_FACTORIES: dict[str, "callable[[], SocialPublisher]"] = {
    "mock_x": lambda: MockXPublisher(),
    "mock_instagram": lambda: MockInstagramPublisher(),
    "telegram": lambda: TelegramPublisher(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    ),
    "linkedin": lambda: LinkedInPublisher(
        access_token=settings.linkedin_access_token,
        person_urn=settings.linkedin_person_urn,
        api_version=settings.linkedin_api_version,
    ),
}

# Which adapter NAME each platform currently routes to — read from
# settings, so this is the config-driven part.
_PLATFORM_TO_ADAPTER_NAME: dict[Platform, str] = {
    Platform.X: settings.adapter_map_x,
    Platform.INSTAGRAM: settings.adapter_map_instagram,
    Platform.TELEGRAM: settings.adapter_map_telegram,
    Platform.LINKEDIN: settings.adapter_map_linkedin,
}


def _build_registry() -> dict[Platform, SocialPublisher]:
    registry: dict[Platform, SocialPublisher] = {}
    for platform, adapter_name in _PLATFORM_TO_ADAPTER_NAME.items():
        factory = _ADAPTER_FACTORIES.get(adapter_name)
        if factory is None:
            raise ValueError(
                f"Unknown adapter name '{adapter_name}' configured for platform "
                f"'{platform.value}'. Valid names: {list(_ADAPTER_FACTORIES.keys())}"
            )
        registry[platform] = factory()
    return registry


_REGISTRY: dict[Platform, SocialPublisher] = _build_registry()


def get_publisher(platform: Platform) -> SocialPublisher:
    try:
        return _REGISTRY[platform]
    except KeyError as exc:
        raise NotImplementedError(
            f"No publisher configured for platform '{platform.value}'."
        ) from exc