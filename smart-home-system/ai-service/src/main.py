"""AI 服务层 FastAPI 主应用 — 连通性测试"""

from fastapi import FastAPI
from src.asr import router as asr_router
from src.nlu import router as nlu_router
from src.tts import router as tts_router

app = FastAPI(title="AI Service", version="0.1.0")

# 内部接口（符合 FRONTEND_API_REQUIREMENTS.md §8 路径约定）
app.include_router(asr_router, prefix="/internal/v1/asr", tags=["ASR"])
app.include_router(nlu_router, prefix="/internal/v1/nlu", tags=["NLU"])
app.include_router(tts_router, prefix="/internal/v1/tts", tags=["TTS"])

# 兼容旧版前缀 /ai/*
app.include_router(asr_router, prefix="/ai/asr", tags=["ASR"])
app.include_router(nlu_router, prefix="/ai/nlu", tags=["NLU"])
app.include_router(tts_router, prefix="/ai/tts", tags=["TTS"])


@app.get("/ai/health", tags=["System"])
async def health_check():
    """服务健康检查（兼容旧版路径）"""
    return {"status": "ok", "service": "ai-service"}


@app.get("/internal/health", tags=["System"])
async def internal_health_check():
    """AI 服务健康检查 — FRONTEND_API_REQUIREMENTS.md §11.2

    Returns:
        dict: 包含服务状态与各模型就绪情况。
    """
    return {
        "status": "ok",
        "models": {
            "asr": "ready",
            "nlu": "ready",
            "tts": "not_loaded",
        },
    }
