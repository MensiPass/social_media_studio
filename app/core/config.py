"""
Central place that reads .env and exposes typed settings to the rest of the app.
Every other file that needs a config value imports `settings` from here —
never reads os.environ directly. One source of truth, fails fast on typos.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    database_url: str

    # --- Redis / Celery ---
    redis_url: str

    # --- Telegram (blank until Day 7) ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # --- LinkedIn (blank until Day 8) ---
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_access_token: str = ""
    linkedin_person_urn: str = ""
    # LinkedIn ships a new API version monthly (YYYYMM format). If posting
    # ever fails with HTTP 426 "Upgrade Required", check the current
    # version at https://learn.microsoft.com/en-us/linkedin/marketing/versioning
    # and update LINKEDIN_API_VERSION in .env — no code change needed.
    linkedin_api_version: str = "202606"

    # --- Crash recovery (added Day 10) ---
    # A slot claimed (PENDING -> PUBLISHING) longer than this without
    # finishing is treated as "the worker that claimed it died" and gets
    # safely re-dispatched. Lower this temporarily for faster live testing.
    stuck_slot_threshold_seconds: int = 120

    # --- Adapter routing (added Day 12) ---
    # Which adapter implementation handles each platform. Changing these
    # values (in .env) swaps adapters WITHOUT touching any code — this is
    # what makes the adapter pattern's config-swap promise actually real,
    # not just theoretical. Valid values: mock_x, mock_instagram,
    # telegram, linkedin.
    adapter_map_x: str = "mock_x"
    adapter_map_instagram: str = "mock_instagram"
    adapter_map_telegram: str = "telegram"
    adapter_map_linkedin: str = "linkedin"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()