from fastapi import APIRouter

from ...services import home_orchestrator

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard")
async def get_dashboard():
    return await home_orchestrator.dashboard()
