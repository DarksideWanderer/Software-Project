"""TTS 子路由 — 连通性测试桩"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """TTS 模块健康检查"""
    return {"status": "ok", "module": "tts"}


@router.post("/synthesize")
async def synthesize():
    """语音合成端点（占位，未实现）"""
    return {
        "status": "not_implemented",
        "module": "tts",
        "message": "语音合成功能尚未实现",
    }
