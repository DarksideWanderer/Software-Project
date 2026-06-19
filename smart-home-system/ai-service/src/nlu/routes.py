"""NLU 子路由 — 规则版 mock 意图解析模块。

本模块实现 FRONTEND_API_REQUIREMENTS.md §8.2 定义的内部 NLU 接口。
当前版本不调用真实大模型，只基于请求中的 devices/scenes 生成受约束动作计划。
"""

import re
from typing import Any, Literal

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

router = APIRouter()


class ConversationMessage(BaseModel):
    role: str | None = None
    content: str | None = None


class DeviceCommand(BaseModel):
    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class DeviceInfo(BaseModel):
    id: str
    type: str
    name: str
    room: str | None = None
    online: bool = True
    commands: list[DeviceCommand] = Field(default_factory=list)


class SceneInfo(BaseModel):
    id: str
    name: str


class InterpretRequest(BaseModel):
    text: str = ""
    conversation: list[ConversationMessage] = Field(default_factory=list)
    devices: list[DeviceInfo] = Field(default_factory=list)
    scenes: list[SceneInfo] = Field(default_factory=list)


class DeviceAction(BaseModel):
    kind: Literal["device_command"] = "device_command"
    device_id: str
    command: str
    params: dict[str, Any] = Field(default_factory=dict)


class SceneAction(BaseModel):
    kind: Literal["scene"] = "scene"
    scene_id: str


Action = DeviceAction | SceneAction


class InterpretResponse(BaseModel):
    understood: bool
    reply: str
    actions: list[Action] = Field(default_factory=list)


DEVICE_KEYWORDS = {
    "light": ("灯", "灯光", "主灯", "氛围灯"),
    "air_conditioner": ("空调",),
    "curtain": ("窗帘",),
}

ROOM_KEYWORDS = ("客厅", "卧室", "书房", "厨房", "阳台")


TURN_ON_WORDS = ("打开", "开启", "启动", "开灯")
TURN_OFF_WORDS = ("关闭", "关掉", "关上", "停止")


@router.get("/health")
async def health():
    """NLU 模块健康检查。"""
    return {"status": "ok", "module": "nlu"}


@router.post("/parse")
async def parse():
    """意图解析端点（占位，未实现）"""
    return {"status": "not_implemented", "module": "nlu", "message": "自然语言理解功能尚未实现"}