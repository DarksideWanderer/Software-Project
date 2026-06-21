from fastapi import APIRouter

from ...services import home_orchestrator

router = APIRouter(prefix="/scenes", tags=["Scenes"])


@router.get("")
async def get_scenes():
    return {"scenes": home_orchestrator.list_scenes()}


@router.post("/{scene_id}/execute")
async def execute_scene(scene_id: str):
    return await home_orchestrator.execute_scene(scene_id)
