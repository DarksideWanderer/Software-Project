from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field

from ...services import home_orchestrator

router = APIRouter(prefix="/assistant", tags=["Assistant"])


class AssistantMessageRequest(BaseModel):
    text: str | None = Field(default=None, description="用户输入的自然语言指令")
    message: str | None = Field(default=None, description="兼容字段：等同于 text")
    conversation: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/messages")
async def send_assistant_message(req: AssistantMessageRequest):
    text = req.text if req.text is not None else req.message
    return await home_orchestrator.execute_assistant_text(text or "", req.conversation)


@router.post("/voice")
async def send_assistant_voice(
    audio: UploadFile = File(...),
    language: str = Form(default="zh-CN"),
):
    return await home_orchestrator.execute_assistant_voice(audio, language)
