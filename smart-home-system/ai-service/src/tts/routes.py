"""TTS 子路由 — 文本转语音合成"""

import os
import uuid
import logging
import asyncio
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


class SynthesizeRequest(BaseModel):
    """语音合成请求参数"""
    text: str = Field(..., description="需要合成语音的文本")
    voice: str = Field(default="Cherry", description="音色名称")


class SynthesizeResponse(BaseModel):
    """语音合成响应（URL 模式）"""
    status: str
    audio_url: Optional[str] = None
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


@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    """将文本合成为语音

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
                    request_id=response.request_id,
                )
            else:
                logger.warning("云端语音合成返回异常 (code=%s)，降级到本地合成",
                               getattr(response, 'code', 'unknown'))
    else:
        logger.warning("未设置 DASHSCOPE_API_KEY，使用本地合成")

    # ---------- 降级：本地 pyttsx3 合成 ----------
    try:
        file_id = uuid.uuid4().hex
        filename = f"{file_id}.wav"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(_tts_executor, _fallback_synthesize, req.text, filename)
        audio_url = f"/ai/tts/audio/{filename}"
        logger.info("本地语音合成成功: %s", audio_url)
        return SynthesizeResponse(
            status="success",
            audio_url=audio_url,
            request_id=None,
        )
    except Exception as e:
        logger.exception("本地语音合成也失败了")
        raise HTTPException(
            status_code=500,
            detail=f"语音合成失败（云端与本地均不可用）: {str(e)}",
        )
