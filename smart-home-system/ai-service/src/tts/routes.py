"""TTS 子路由 — 文本转语音合成"""

import os
import time
import uuid
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

from dotenv import load_dotenv
load_dotenv()

DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/api/v1"

# 本地 fallback 合成配置
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "generated_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
_tts_executor = ThreadPoolExecutor(max_workers=1)

# ---------- 过期音频清理 ----------
AUDIO_MAX_AGE_SECONDS: int = 1800  # 30 分钟
AUDIO_CLEANUP_INTERVAL_SECONDS: int = 600  # 每 10 分钟清理一次


def _cleanup_expired_audio() -> int:
    """删除超过 AUDIO_MAX_AGE_SECONDS 的音频文件，返回删除数量"""
    if not os.path.isdir(AUDIO_DIR):
        return 0
    now = time.time()
    count = 0
    for fname in os.listdir(AUDIO_DIR):
        fpath = os.path.join(AUDIO_DIR, fname)
        if not (fname.endswith(".wav") or fname.endswith(".mp3")) or not os.path.isfile(fpath):
            continue
        try:
            age = now - os.path.getmtime(fpath)
            if age > AUDIO_MAX_AGE_SECONDS:
                os.remove(fpath)
                count += 1
                logger.debug("已删除过期音频: %s (age=%.1fs)", fname, age)
        except OSError:
            logger.warning("无法删除音频文件: %s", fname)
    if count:
        logger.info("过期音频清理完成，共删除 %d 个文件", count)
    return count


async def cleanup_audio_background():
    """后台协程：定期清理过期音频"""
    while True:
        await asyncio.sleep(AUDIO_CLEANUP_INTERVAL_SECONDS)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _cleanup_expired_audio)


class SynthesizeRequest(BaseModel):
    """语音合成请求参数"""
    text: str = Field(..., description="需要合成语音的文本")
    voice: str = Field(default="default", description="音色名称")
    format: str = Field(default="mp3", description="音频格式，支持 mp3/wav")


def _resolve_content_type(fmt: str) -> str:
    """将请求中的 format 值映射为标准 MIME 类型"""
    mapping = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "webm": "audio/webm",
    }
    return mapping.get(fmt, f"audio/{fmt}")


class SynthesizeResponse(BaseModel):
    """语音合成响应（URL 模式）"""
    status: str
    audio_url: Optional[str] = None
    content_type: Optional[str] = None
    expires_at: Optional[str] = None
    request_id: Optional[str] = None
    message: Optional[str] = None


@router.get("/health")
async def health():
    """TTS 模块健康检查"""
    return {"status": "ok", "module": "tts"}


@router.post("/synthesize")
async def synthesize():
    """语音合成端点（占位，未实现）"""
    return {"status": "not_implemented", "module": "tts", "message": "语音合成功能尚未实现"}