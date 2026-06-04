from pydantic import BaseModel, Field
from typing import Any, Optional


class CommandRequest(BaseModel):
    """通用命令请求 — 任意设备通用"""
    command: str = Field(..., description="命令名称")
    params: dict = Field(default_factory=dict, description="命令参数")


class CommandResponse(BaseModel):
    """通用命令响应 — C++ 返回的原始 JSON 透传"""
    success: bool = Field(False)
    message: str = Field("")
    state: Optional[dict] = None

