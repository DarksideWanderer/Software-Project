from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...services import home_orchestrator

router = APIRouter(prefix="/device-commands", tags=["Device Commands"])


class BatchCommandItem(BaseModel):
    device_id: str
    command: str
    params: dict[str, Any] = Field(default_factory=dict)


class BatchCommandRequest(BaseModel):
    request_id: str | None = None
    commands: list[BatchCommandItem]


@router.post("/batch")
async def execute_batch(req: BatchCommandRequest):
    payload = [item.dict() for item in req.commands]
    result = await home_orchestrator.execute_batch(payload)
    return {"request_id": req.request_id, **result}
