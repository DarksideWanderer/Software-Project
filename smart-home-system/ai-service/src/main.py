"""AI 服务层 FastAPI 主应用 — 连通性测试"""

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.asr import router as asr_router
from src.nlu import router as nlu_router
from src.tts import router as tts_router
from src.tts.routes import cleanup_audio_background, _cleanup_expired_audio


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时清理过期音频 + 后台定期清理"""
    # startup
    _cleanup_expired_audio()
    task = asyncio.create_task(cleanup_audio_background())
    yield
    # shutdown
    task.cancel()


app = FastAPI(title="AI Service", version="0.1.0", lifespan=lifespan)

app.include_router(asr_router, prefix="/ai/asr", tags=["ASR"])
app.include_router(nlu_router, prefix="/ai/nlu", tags=["NLU"])
app.include_router(tts_router, prefix="/ai/tts", tags=["TTS"])

# 挂载本地 TTS 生成音频文件的静态目录，供客户端下载
tts_audio_dir = os.path.join(os.path.dirname(__file__), "tts", "generated_audio")
os.makedirs(tts_audio_dir, exist_ok=True)
app.mount("/ai/tts/audio", StaticFiles(directory=tts_audio_dir), name="tts_audio")


@app.get("/ai/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """服务健康检查"""
    return {"status": "ok", "service": "ai-service"}