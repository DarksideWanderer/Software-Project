from fastapi import APIRouter

from .assistant import router as assistant_router
from .audio import router as audio_router
from .commands import router as commands_router
from .dashboard import router as dashboard_router
from .devices import router as devices_router
from .scenes import router as scenes_router

## @file __init__.py
# @brief API V1 路由定义文件
# @details 汇总并挂载系统版本 1 的所有功能模块路由

router = APIRouter()

# 挂载设备仿真路由
router.include_router(devices_router)
router.include_router(commands_router)
router.include_router(scenes_router)
router.include_router(assistant_router)
router.include_router(audio_router)
router.include_router(dashboard_router)

## @brief 获取系统概览信息
# @details 返回当前 API 版本的相关信息及支持的功能特性列表
# @return 返回包含版本和功能列表的字典
@router.get("/info", tags=["General"])
async def get_system_info():
    return {
        "version": "v1",
        "supported_features": [
            "device_control",
            "scene_execution",
            "assistant_text",
            "assistant_voice",
            "assistant_tts",
            "dashboard",
        ],
    }
