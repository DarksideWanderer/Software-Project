"""NLU 子路由 — 连通性测试桩"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """NLU 模块健康检查"""
    return {"status": "ok", "module": "nlu"}


@router.post("/parse")
async def parse():
    """意图解析端点（占位，未实现）"""
    return {
        "status": "not_implemented",
        "module": "nlu",
        "message": "自然语言理解功能尚未实现",
    }
