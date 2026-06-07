import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class Settings:
    """Runtime settings for future external AI provider integration."""

    service_name: str = "Smart Home AI Service"
    iflytek_app_id: str | None = field(default_factory=lambda: os.getenv("IFLYTEK_APP_ID"))
    iflytek_api_key: str | None = field(default_factory=lambda: os.getenv("IFLYTEK_API_KEY"))
    iflytek_api_secret: str | None = field(
        default_factory=lambda: os.getenv("IFLYTEK_API_SECRET")
    )
    deepseek_api_key: str | None = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY")
    )
    deepseek_model: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    )
    deepseek_base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    llm_api_key: str | None = field(default_factory=lambda: os.getenv("LLM_API_KEY"))


settings = Settings()
