"""ASR 子路由 — 连通性测试桩"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """ASR 模块健康检查"""
    return {"status": "ok", "module": "asr"}


@router.post("/transcribe")
async def transcribe():
    """语音识别端点（占位，未实现）"""
    return {"status": "not_implemented", "module": "asr", "message": "语音识别功能尚未实现"}