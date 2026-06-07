from typing import Literal

from pydantic import BaseModel, Field


Intent = Literal[
    "device_control",
    "device_query",
    "weather_query",
    "reminder_create",
    "scene_mode",
    "unknown",
]

Action = Literal[
    "turn_on",
    "turn_off",
    "set_temperature",
    "increase_temperature",
    "decrease_temperature",
    "set_brightness",
    "increase_brightness",
    "decrease_brightness",
    "open",
    "close",
    "set_open_percent",
    "query_status",
]


class NluContext(BaseModel):
    user_id: str | None = None
    last_device_type: str | None = None
    last_location: str | None = None


class NluRequest(BaseModel):
    text: str = Field(..., min_length=1, description="User command text")
    context: NluContext | None = None


class Slots(BaseModel):
    device_type: str | None = None
    location: str | None = None
    action: str | None = None
    value: int | float | str | None = None
    unit: str | None = None
    city: str | None = None
    datetime: str | None = None
    content: str | None = None


class NluResponse(BaseModel):
    success: bool
    intent: Intent
    confidence: float = Field(..., ge=0, le=1)
    slots: Slots
    need_clarification: bool = False
    reply: str


class AsrRequest(BaseModel):
    audio_base64: str = ""
    format: str = "wav"
    sample_rate: int = 16000
    mock_text: str | None = None


class AsrResponse(BaseModel):
    success: bool
    text: str
    confidence: float = Field(..., ge=0, le=1)
    provider: str
    message: str = ""


class HealthResponse(BaseModel):
    status: str
    service: str
    supported_intents: list[str]
    supported_actions: list[str]
    external_providers_configured: dict[str, bool]
