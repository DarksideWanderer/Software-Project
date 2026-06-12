"""AI 服务层 FastAPI 主应用 — 连通性测试"""

from fastapi import FastAPI
from src.asr import router as asr_router
from src.nlu import router as nlu_router
from src.tts import router as tts_router

app = FastAPI(title="AI Service", version="0.1.0")

app.include_router(asr_router, prefix="/ai/asr", tags=["ASR"])
app.include_router(nlu_router, prefix="/ai/nlu", tags=["NLU"])
app.include_router(tts_router, prefix="/ai/tts", tags=["TTS"])


@app.get("/ai/health", tags=["System"])
async def health_check():
    """服务健康检查"""
    return {"status": "ok", "service": "ai-service"}