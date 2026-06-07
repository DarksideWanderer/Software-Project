import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings for future external AI provider integration."""

    service_name: str = "Smart Home AI Service"
    iflytek_app_id: str | None = os.getenv("IFLYTEK_APP_ID")
    iflytek_api_key: str | None = os.getenv("IFLYTEK_API_KEY")
    iflytek_api_secret: str | None = os.getenv("IFLYTEK_API_SECRET")
    llm_api_key: str | None = os.getenv("LLM_API_KEY")


settings = Settings()
