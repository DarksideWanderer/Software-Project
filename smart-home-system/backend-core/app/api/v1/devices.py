"""设备 API 路由。

保留底层 DeviceHub 调试接口，同时为课程交付前端提供统一设备模型。
"""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...core.device_simulator import hub
from ...schemas.device import CommandRequest, CommandResponse
from ...services import home_orchestrator

router = APIRouter(prefix="/devices", tags=["Devices"])


class DeviceCommandRequest(BaseModel):
    command: str = Field(..., description="设备命令名称")
    params: dict[str, Any] = Field(default_factory=dict, description="命令参数")


@router.get("")
async def get_devices():
    """获取三设备课程演示模型。"""
    return {"devices": await home_orchestrator.list_devices()}


@router.get("/raw")
async def get_raw_devices():
    """获取 DeviceHub 原始注册信息，供调试使用。"""
    return {"devices": hub.list_devices()}


@router.get("/{device_id}")
async def get_device(device_id: str):
    """获取单设备统一状态模型。"""
    return {"device": await home_orchestrator.get_device(device_id)}


@router.get("/{device_id}/state")
async def get_device_state(device_id: str):
    """查询设备当前状态"""
    return await hub.get_state(device_id)


@router.get("/{device_id}/commands/count")
async def get_device_command_count(device_id: str):
    """查询某个设备有什么命令"""
    return hub.get_command_count(device_id)

@router.get("/{device_id}/commands/{command_name}")
async def get_device_command_schema(device_id: str, command_name: str):
    """查询某个设备的某个命令的调用格式"""
    return hub.get_command_schema(device_id, command_name)


@router.post("/{device_id}/commands")
async def execute_product_device_command(device_id: str, req: DeviceCommandRequest):
    """执行产品层设备命令，并返回统一设备状态。"""
    return await home_orchestrator.execute_device_command(device_id, req.command, req.params)


@router.post("/{device_id}/command", response_model=CommandResponse)
async def device_command(device_id: str, req: CommandRequest):
    """向设备发送命令"""
    return await hub.send_command(device_id, req.command, req.params)

