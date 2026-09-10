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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()