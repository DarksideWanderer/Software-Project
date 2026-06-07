from fastapi import FastAPI

from .asr import transcribe_audio
from .config import settings
from .nlu import SUPPORTED_ACTIONS, SUPPORTED_INTENTS, parse_text
from .schemas import AsrRequest, AsrResponse, HealthResponse, NluRequest, NluResponse


app = FastAPI(
    title="Smart Home AI Service",
    description="ASR mock and rule-based NLU service for the smart home assistant.",
    version="1.0.0",
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        supported_intents=SUPPORTED_INTENTS,
        supported_actions=SUPPORTED_ACTIONS,
        external_providers_configured={
            "iflytek": bool(
                settings.iflytek_app_id
                and settings.iflytek_api_key
                and settings.iflytek_api_secret
            ),
            "llm": bool(settings.llm_api_key),
        },
    )


@app.post("/ai/nlu", response_model=NluResponse, tags=["AI"])
async def nlu(request: NluRequest) -> NluResponse:
    return parse_text(request.text, request.context)


@app.post("/ai/asr", response_model=AsrResponse, tags=["AI"])
async def asr(request: AsrRequest) -> AsrResponse:
    return transcribe_audio(request)
