"""TTS 子路由 — 文本转语音合成

实现 FRONTEND_API_REQUIREMENTS.md §8.3 定义的 TTS 内部接口。

采用双引擎降级策略：
1. 云端引擎 — 阿里云百炼 Qwen-TTS（DashScope SDK）
2. 本地降级 — pyttsx3（离线合成，仅支持 WAV 格式）
"""

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


# ── 本地 pyttsx3 合成 ────────────────────────────────────────────────────

def _synthesize_local(text: str, fmt: str = "wav") -> tuple[str, str]:
    """使用 pyttsx3 进行本地离线语音合成。

    Args:
        text: 待合成文本。
        fmt: 目标格式（pyttsx3 仅支持 wav）。

    Returns:
        (file_path, content_type) 元组。

    Raises:
        RuntimeError: pyttsx3 初始化或合成失败。
    """
    import pyttsx3

    file_id = uuid.uuid4().hex
    ext = "wav"
    file_path = os.path.join(AUDIO_DIR, f"{file_id}.{ext}")

    try:
        engine = pyttsx3.init()
    except Exception as e:
        raise RuntimeError(f"pyttsx3 初始化失败: {e}")

    try:
        engine.save_to_file(text, file_path)
        engine.runAndWait()
    except Exception as e:
        raise RuntimeError(f"pyttsx3 合成失败: {e}")

    if not os.path.isfile(file_path) or os.path.getsize(file_path) == 0:
        raise RuntimeError("pyttsx3 合成失败：未生成有效音频文件")

    return file_path, "audio/wav"


# ── 云端 DashScope 合成 ──────────────────────────────────────────────────

def _synthesize_dashscope(
    text: str, voice: str = "Cherry", api_key: str | None = None
) -> dict | None:
    """使用阿里云 DashScope Qwen-TTS 进行云端语音合成。

    Args:
        text: 待合成文本。
        voice: 音色名称。
        api_key: DashScope API Key（未提供时从环境变量读取）。

    Returns:
        成功时返回 {"audio_url", "request_id", "content_type"}；
        失败或不可用时返回 None。
    """
    try:
        import dashscope
        from dashscope.audio.qwen_tts import SpeechSynthesizer

        key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        if not key:
            logger.info("未配置 DASHSCOPE_API_KEY，跳过云端合成")
            return None

        response = SpeechSynthesizer.call(
            model="qwen-tts",
            api_key=key,
            text=text,
            voice=voice,
        )

        if response.status_code != 200 or response.code:
            logger.warning(
                "DashScope TTS 失败: status=%s code=%s message=%s",
                response.status_code,
                response.code,
                response.message,
            )
            return None

        audio_url = response.output.audio.url if response.output.audio else None
        if not audio_url:
            logger.warning("DashScope 返回空音频 URL")
            return None

        expires_at = None
        if response.output.audio.expires_at:
            expires_at = datetime.fromtimestamp(
                response.output.audio.expires_at, tz=timezone.utc
            ).isoformat()

        return {
            "audio_url": audio_url,
            "request_id": response.request_id,
            "content_type": "audio/wav",
            "expires_at": expires_at,
        }

    except ImportError:
        logger.warning("dashscope 未安装，跳过云端合成")
        return None
    except Exception as e:
        logger.warning("DashScope TTS 异常: %s", e)
        return None


# ── 路由端点 ─────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    """TTS 模块健康检查"""
    return {"status": "ok", "module": "tts"}


def _build_local_response(file_path: str, content_type: str, audio_prefix: str = "/internal/v1/tts/audio") -> dict:
    """构建本地合成成功响应。"""
    file_name = os.path.basename(file_path)
    return {
        "status": "success",
        "audio_url": f"{audio_prefix}/{file_name}",
        "content_type": content_type,
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=AUDIO_MAX_AGE_SECONDS)
        ).isoformat(),
        "request_id": None,
    }


@router.post("/speech")
async def speech(request: SynthesizeRequest):
    """TTS 语音合成主端点 — FRONTEND_API_REQUIREMENTS.md §8.3。

    路径: POST /internal/v1/tts/speech

    优先使用 DashScope 云端合成，失败时降级到本地 pyttsx3。
    """
    return await _handle_synthesize(request, audio_prefix="/internal/v1/tts/audio")


@router.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    """语音合成端点（兼容旧版路径）— 复用 /speech 逻辑。"""
    return await _handle_synthesize(request, audio_prefix="/ai/tts/audio")


async def _handle_synthesize(request: SynthesizeRequest, audio_prefix: str = "/internal/v1/tts/audio") -> dict:
    """语音合成核心逻辑：云端优先，本地降级。"""
    text = request.text
    voice = request.voice if request.voice != "default" else "Cherry"
    fmt = request.format

    # 1. 尝试云端合成
    cloud_result = _synthesize_dashscope(text=text, voice=voice)
    if cloud_result:
        return {
            "status": "success",
            "audio_url": cloud_result["audio_url"],
            "content_type": cloud_result.get("content_type", "audio/wav"),
            "expires_at": cloud_result.get("expires_at"),
            "request_id": cloud_result.get("request_id"),
        }

    # 2. 降级到本地 pyttsx3 合成
    try:
        file_path, content_type = _synthesize_local(text=text, fmt=fmt)
        return _build_local_response(file_path, content_type, audio_prefix)
    except Exception as e:
        logger.error("本地 TTS 合成失败: %s", e)
        raise HTTPException(
            status_code=500,
            detail="语音合成失败，云端和本地引擎均不可用",
        )