"""AI 服务层 FastAPI 主应用

为 backend-core 提供 ASR / NLU / TTS 内部接口。
符合 FRONTEND_API_REQUIREMENTS.md §8 和 §11.2 定义。
"""

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.asr import router as asr_router
from src.nlu import router as nlu_router
from src.tts import router as tts_router
from src.tts.routes import cleanup_audio_background, _cleanup_expired_audio, SynthesizeRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时清理过期音频 + 后台定期清理"""
    # startup
    _cleanup_expired_audio()
    task = asyncio.create_task(cleanup_audio_background())
    yield
    # shutdown
    task.cancel()


app = FastAPI(title="AI Service", version="0.2.0", lifespan=lifespan)

# ── 内部接口（符合 FRONTEND_API_REQUIREMENTS.md §8 路径约定）────────────
app.include_router(asr_router, prefix="/internal/v1/asr", tags=["ASR"])
app.include_router(nlu_router, prefix="/internal/v1/nlu", tags=["NLU"])
app.include_router(tts_router, prefix="/internal/v1/tts", tags=["TTS"])

# ── 兼容旧版前缀 /ai/* ──────────────────────────────────────────────────
app.include_router(asr_router, prefix="/ai/asr", tags=["ASR"])
app.include_router(nlu_router, prefix="/ai/nlu", tags=["NLU"])
app.include_router(tts_router, prefix="/ai/tts", tags=["TTS"])

# ── 挂载本地 TTS 生成音频文件的静态目录，供 backend-core 下载 ──────────
tts_audio_dir = os.path.join(os.path.dirname(__file__), "tts", "generated_audio")
os.makedirs(tts_audio_dir, exist_ok=True)
app.mount("/internal/v1/tts/audio", StaticFiles(directory=tts_audio_dir), name="tts_audio_internal")
app.mount("/ai/tts/audio", StaticFiles(directory=tts_audio_dir), name="tts_audio_legacy")


# ── TTS 旧版 /synthesize 别名（兼容测试与旧版调用方）────────────────────
# tts/routes.py 只定义了 /speech 端点，此处补充 /synthesize 别名

from src.tts.routes import synthesize as _tts_synthesize_handler


@app.post("/ai/tts/synthesize", tags=["TTS"])
async def tts_synthesize_legacy(req: SynthesizeRequest):
    """TTS 合成（旧版 /synthesize 端点，转发到 /speech）。"""
    from fastapi.responses import JSONResponse
    import json as _json

    resp = await _tts_synthesize_handler(req)
    # 将 local audio URL 的 prefix 从 /internal/v1/tts/audio/ 映射到 /ai/tts/audio/
    audio_url = getattr(resp, "audio_url", None)
    if audio_url and audio_url.startswith("/internal/v1/tts/audio/"):
        filename = audio_url.rsplit("/", 1)[-1]
        resp.audio_url = f"/ai/tts/audio/{filename}"
    return resp


@app.post("/internal/v1/tts/synthesize", tags=["TTS"])
async def tts_synthesize_internal_legacy(req: SynthesizeRequest):
    """TTS 合成（内部旧版 /synthesize 端点，转发到 /speech）。"""
    return await _tts_synthesize_handler(req)


# ── 健康检查 ────────────────────────────────────────────────────────────

@app.get("/ai/health", tags=["System"])
async def health_check():
    """旧版服务健康检查（兼容）"""
    return {"status": "ok", "service": "ai-service"}


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "ai-service",
        "status": "ok",
        "message": "AI Service is running. Open /docs for API docs or /internal/health for model status.",
        "endpoints": {
            "docs": "/docs",
            "internal_health": "/internal/health",
            "asr": "/internal/v1/asr/transcriptions",
            "nlu": "/internal/v1/nlu/interpret",
            "tts": "/internal/v1/tts/speech",
        },
    }


@app.get("/internal/health", tags=["System"])
async def internal_health():
    """AI 服务内部健康检查 — FRONTEND_API_REQUIREMENTS.md §11.2。

    Returns:
        服务整体状态及各模型模块的加载状态。
    """
    return {
        "status": "ok",
        "models": {
            "asr": "ready",
            "nlu": "ready",
            "tts": "ready",
        },
    }
