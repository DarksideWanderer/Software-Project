from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field

from ...services import home_orchestrator

router = APIRouter(prefix="/assistant", tags=["Assistant"])


class AssistantMessageRequest(BaseModel):
    text: str = Field(..., description="用户输入的自然语言指令")
    conversation: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/messages")
async def send_assistant_message(req: AssistantMessageRequest):
    return await home_orchestrator.execute_assistant_text(req.text, req.conversation)


@router.post("/voice")
async def send_assistant_voice(
    audio: UploadFile = File(...),
    language: str = Form(default="zh-CN"),
):
    return await home_orchestrator.execute_assistant_voice(audio, language)
