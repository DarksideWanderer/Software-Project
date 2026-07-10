from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...services import home_orchestrator

router = APIRouter(prefix="/scenes", tags=["Scenes"])


class SceneCommandRequest(BaseModel):
    device_id: str
    command: str
    params: dict[str, Any] = Field(default_factory=dict)


class SceneCreateRequest(BaseModel):
    name: str
    description: str | None = ""
    commands: list[SceneCommandRequest] = Field(default_factory=list)


class NaturalSceneRequest(BaseModel):
    text: str


@router.get("")
async def get_scenes():
    return {"scenes": home_orchestrator.list_scenes()}


@router.post("")
async def create_scene(req: SceneCreateRequest):
    scene = home_orchestrator.create_scene(
        name=req.name,
        description=req.description or "",
        commands=[cmd.dict() for cmd in req.commands],
    )
    return {"scene": scene, "scenes": home_orchestrator.list_scenes()}


@router.post("/natural")
async def create_scene_from_text(req: NaturalSceneRequest):
    return await home_orchestrator.create_scene_from_text(req.text)


@router.post("/{scene_id}/execute")
async def execute_scene(scene_id: str):
    return await home_orchestrator.execute_scene(scene_id)


@router.delete("/{scene_id}")
async def delete_scene(scene_id: str):
    return home_orchestrator.delete_scene(scene_id)
