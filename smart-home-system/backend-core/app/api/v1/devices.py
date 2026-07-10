from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...core.device_simulator import hub
from ...schemas.device import CommandRequest, CommandResponse
from ...services import home_orchestrator

router = APIRouter(prefix="/devices", tags=["Devices"])


class DeviceCommandRequest(BaseModel):
    command: str = Field(..., description="Device command name")
    params: dict[str, Any] = Field(default_factory=dict, description="Command params")


class BindDeviceRequest(BaseModel):
    name: str | None = Field(default=None, description="User visible device name")
    room: str | None = Field(default=None, description="Room name")


class UpdateDeviceRequest(BaseModel):
    name: str | None = Field(default=None, description="User visible device name")
    room: str | None = Field(default=None, description="Room name")


@router.get("")
async def get_devices():
    return {"devices": await home_orchestrator.list_devices()}


@router.get("/discover")
async def discover_devices():
    return {"devices": home_orchestrator.discover_devices()}


@router.get("/raw")
async def get_raw_devices():
    return {"devices": hub.list_devices()}


@router.get("/{device_id}")
async def get_device(device_id: str):
    return {"device": await home_orchestrator.get_device(device_id)}


@router.post("/{device_id}/bind")
async def bind_device(device_id: str, req: BindDeviceRequest):
    result = home_orchestrator.bind_device(device_id, req.name, req.room)
    return {
        **result,
        "devices": await home_orchestrator.list_devices(),
        "candidates": home_orchestrator.discover_devices(),
        "scenes": home_orchestrator.list_scenes(),
    }


@router.patch("/{device_id}")
async def update_device(device_id: str, req: UpdateDeviceRequest):
    result = home_orchestrator.update_bound_device(device_id, req.name, req.room)
    return {**result, "device": await home_orchestrator.get_device(device_id), "devices": await home_orchestrator.list_devices()}


@router.delete("/{device_id}")
async def remove_device(device_id: str):
    result = await home_orchestrator.remove_device(device_id)
    return {**result, "candidates": home_orchestrator.discover_devices()}


@router.get("/{device_id}/state")
async def get_device_state(device_id: str):
    return await hub.get_state(device_id)


@router.get("/{device_id}/commands/count")
async def get_device_command_count(device_id: str):
    return hub.get_command_count(device_id)


@router.get("/{device_id}/commands/{command_name}")
async def get_device_command_schema(device_id: str, command_name: str):
    return hub.get_command_schema(device_id, command_name)


@router.post("/{device_id}/commands")
async def execute_product_device_command(device_id: str, req: DeviceCommandRequest):
    return await home_orchestrator.execute_device_command(device_id, req.command, req.params)


@router.post("/{device_id}/command", response_model=CommandResponse)
async def device_command(device_id: str, req: CommandRequest):
    return await hub.send_command(device_id, req.command, req.params)
