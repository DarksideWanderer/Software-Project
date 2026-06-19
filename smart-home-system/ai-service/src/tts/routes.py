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


def _fallback_synthesize(text: str, filename: str) -> str:
    """使用 pyttsx3 本地合成语音（同步函数，运行在独立线程中）"""
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    filepath = os.path.join(AUDIO_DIR, filename)
    engine.save_to_file(text, filepath)
    engine.runAndWait()
    return filepath


@router.post("/speech")
async def synthesize(req: SynthesizeRequest):
    """文本转语音合成

    优先调用阿里云百炼 Qwen-TTS（DashScope SDK）。
    若云端不可用（如网络异常、无 API Key、服务超时等），
    自动降级为本地 pyttsx3 合成。
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")

    # ---------- 尝试云端 DashScope ----------
    if api_key:
        try:
            import dashscope
            dashscope.base_http_api_url = DASHSCOPE_API_URL
            text = req.text
            response = dashscope.audio.qwen_tts.SpeechSynthesizer.call(
                model="qwen-tts",
                api_key=api_key,
                text=text,
                voice=req.voice,
            )

        except ImportError:
            logger.warning("dashscope SDK 未安装，降级到本地合成")
        except Exception as e:
            logger.warning("云端语音合成失败 (%s)，降级到本地合成", e)
        else:
            if response.status_code == 200 and response.output and response.output.audio and response.output.audio.url:
                return SynthesizeResponse(
                    status="success",
                    audio_url=response.output.audio.url,
                    content_type=_resolve_content_type(req.format),
                    request_id=response.request_id,
                )
            else:
                logger.warning("云端语音合成返回异常 (code=%s)，降级到本地合成",
                               getattr(response, 'code', 'unknown'))
    else:
        logger.warning("未设置 DASHSCOPE_API_KEY，使用本地合成")

    # ---------- 降级：本地 pyttsx3 合成 ----------
    try:
        if req.format != "wav":
            logger.info("请求格式为 '%s'，本地合成仅支持 wav，将输出 wav 格式", req.format)
        file_id = uuid.uuid4().hex
        filename = f"{file_id}.wav"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(_tts_executor, _fallback_synthesize, req.text, filename)
        audio_url = f"/internal/v1/tts/audio/{filename}"
        tz_cst = timezone(timedelta(hours=8))
        expires_at = (datetime.now(tz_cst) + timedelta(seconds=AUDIO_MAX_AGE_SECONDS)).strftime("%Y-%m-%dT%H:%M:%S%z")
        expires_at = expires_at[:-2] + ":" + expires_at[-2:]  # "YYYY-MM-DDTHH:MM:SS+0800" → "YYYY-MM-DDTHH:MM:SS+08:00"
        logger.info("本地语音合成成功: %s", audio_url)
        return SynthesizeResponse(
            status="success",
            audio_url=audio_url,
            content_type="audio/wav",
            expires_at=expires_at,
            request_id=None,
        )
    except Exception as e:
        logger.exception("本地语音合成也失败了")
        raise HTTPException(
            status_code=500,
            detail=f"语音合成失败（云端与本地均不可用）: {str(e)}",
        )