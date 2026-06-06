"""
设备 API 路由 — 通用动态路由

所有设备通过 TCP 注册后，自动获得以下 API：
  GET  /api/v1/devices                     → 列出所有设备
  GET  /api/v1/devices/{device_id}/state   → 查询设备状态
  POST /api/v1/devices/{device_id}/command → 发送命令
"""
from fastapi import APIRouter

from ...schemas.device import CommandRequest, CommandResponse
from ...core.device_simulator import hub

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("")
async def get_devices():
    """获取所有已注册设备及其命令列表"""
    return {"devices": hub.list_devices()}


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

@router.post("/{device_id}/command", response_model=CommandResponse)
async def device_command(device_id: str, req: CommandRequest):
    """向设备发送命令"""
    return await hub.send_command(device_id, req.command, req.params)

