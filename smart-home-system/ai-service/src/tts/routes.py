"""TTS 子路由 — 文本转语音合成"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

from dotenv import load_dotenv
load_dotenv()

DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/api/v1"


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


@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    """将文本合成为语音

    支持两种返回模式：
      - return_audio_data=False（默认）：返回 JSON，包含可下载的音频 URL
      - return_audio_data=True：直接返回音频二进制数据（WAV）

    使用阿里云百炼 Qwen-TTS 模型（DashScope SDK）进行非实时语音合成。
    API Key 通过环境变量 DASHSCOPE_API_KEY 配置。
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="服务配置错误：未设置 DASHSCOPE_API_KEY 环境变量",
        )

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
        raise HTTPException(
            status_code=500,
            detail="服务错误：dashscope SDK 未安装",
        )
    except Exception as e:
        logger.exception("语音合成调用失败")
        raise HTTPException(
            status_code=502,
            detail=f"语音合成服务调用失败: {str(e)}",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"语音合成服务返回错误: code={response.code}, message={response.message}",
        )

    audio_url = response.output.audio.url if response.output.audio else None
    request_id = response.request_id

    if not audio_url:
        raise HTTPException(
            status_code=502,
            detail="语音合成服务返回结果中缺少音频数据",
        )

    return SynthesizeResponse(
        status="success",
        audio_url=audio_url,
        request_id=request_id,
    )
