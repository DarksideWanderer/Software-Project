from __future__ import annotations

import os
import uuid
from typing import Any

import httpx
from fastapi import HTTPException, UploadFile, status

from ..core.device_simulator import hub


AI_SERVICE_BASE_URL = os.getenv("AI_SERVICE_BASE_URL", "http://127.0.0.1:8001").rstrip("/")

DEVICE_CATALOG: dict[str, dict[str, Any]] = {
    "ac-001": {
        "id": "ac-001",
        "type": "air_conditioner",
        "name": "中央空调",
        "room": "客厅",
        "icon": "icon-ac",
        "color": "#4488a5",
        "soft": "#e0eff5",
        "glow": "rgba(134, 184, 215, .36)",
        "energy": "1.2 kWh",
        "defaults": {"device_id": "ac-001", "device_type": "air_conditioner", "is_on": False, "temperature": 24},
        "commands": {
            "turn_on": {"description": "打开空调", "params": {}},
            "turn_off": {"description": "关闭空调", "params": {}},
            "set_temperature": {
                "description": "设置温度",
                "params": {"temperature": {"type": "integer", "min": 16, "max": 30}},
            },
        },
    },
    "light-001": {
        "id": "light-001",
        "type": "light",
        "name": "客厅主灯",
        "room": "客厅",
        "icon": "icon-light",
        "color": "#ad8038",
        "soft": "#f5ead5",
        "glow": "rgba(237, 182, 94, .36)",
        "energy": "0.3 kWh",
        "defaults": {"device_id": "light-001", "device_type": "light", "is_on": False, "brightness": 70, "color": "daylight"},
        "commands": {
            "turn_on": {"description": "打开灯光", "params": {}},
            "turn_off": {"description": "关闭灯光", "params": {}},
            "set_brightness": {
                "description": "设置亮度",
                "params": {"brightness": {"type": "integer", "min": 0, "max": 100}},
            },
            "set_color": {
                "description": "设置色温",
                "params": {"color": {"type": "string", "values": ["warm", "cool", "daylight"]}},
            },
        },
    },
    "tv-001": {
        "id": "tv-001",
        "type": "tv",
        "name": "智能电视",
        "room": "客厅",
        "icon": "icon-tv",
        "color": "#7566a0",
        "soft": "#e9e5f3",
        "glow": "rgba(158, 145, 200, .3)",
        "energy": "0.8 kWh",
        "defaults": {"device_id": "tv-001", "device_type": "tv", "is_on": False, "channel": 1, "volume": 30},
        "commands": {
            "turn_on": {"description": "打开电视", "params": {}},
            "turn_off": {"description": "关闭电视", "params": {}},
            "set_channel": {
                "description": "切换频道",
                "params": {"channel": {"type": "integer", "min": 1, "max": 999}},
            },
            "set_volume": {
                "description": "设置音量",
                "params": {"volume": {"type": "integer", "min": 0, "max": 100}},
            },
        },
    },
}

SCENES: dict[str, dict[str, Any]] = {
    "home": {
        "id": "home",
        "name": "回家模式",
        "description": "打开客厅主灯和空调，恢复舒适温度。",
        "commands": [
            {"device_id": "light-001", "command": "turn_on", "params": {}},
            {"device_id": "light-001", "command": "set_brightness", "params": {"brightness": 70}},
            {"device_id": "ac-001", "command": "turn_on", "params": {}},
            {"device_id": "ac-001", "command": "set_temperature", "params": {"temperature": 24}},
        ],
    },
    "movie": {
        "id": "movie",
        "name": "观影模式",
        "description": "打开电视、压低灯光，并保持空调舒适。",
        "commands": [
            {"device_id": "tv-001", "command": "turn_on", "params": {}},
            {"device_id": "tv-001", "command": "set_volume", "params": {"volume": 28}},
            {"device_id": "light-001", "command": "turn_on", "params": {}},
            {"device_id": "light-001", "command": "set_brightness", "params": {"brightness": 18}},
            {"device_id": "ac-001", "command": "turn_on", "params": {}},
            {"device_id": "ac-001", "command": "set_temperature", "params": {"temperature": 24}},
        ],
    },
    "away": {
        "id": "away",
        "name": "离家模式",
        "description": "关闭演示设备，进入节能状态。",
        "commands": [
            {"device_id": "tv-001", "command": "turn_off", "params": {}},
            {"device_id": "light-001", "command": "turn_off", "params": {}},
            {"device_id": "ac-001", "command": "turn_off", "params": {}},
        ],
    },
}


def _catalog_or_404(device_id: str) -> dict[str, Any]:
    device = DEVICE_CATALOG.get(device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown device: {device_id}")
    return device


def _is_connected(device_id: str) -> bool:
    return device_id in hub._devices


def _capabilities(device_id: str) -> list[dict[str, Any]]:
    catalog = _catalog_or_404(device_id)
    return [
        {"name": name, "description": meta["description"], "params": meta["params"]}
        for name, meta in catalog["commands"].items()
    ]


def _coerce_params(device_id: str, command: str, params: dict[str, Any] | None) -> dict[str, Any]:
    catalog = _catalog_or_404(device_id)
    command_meta = catalog["commands"].get(command)
    if not command_meta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{device_id} does not support command {command}",
        )

    params = params or {}
    coerced: dict[str, Any] = {}
    for name, schema in command_meta["params"].items():
        if name not in params:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing parameter {name} for command {command}",
            )
        value = params[name]
        if schema["type"] == "integer":
            try:
                number = int(value)
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter {name} must be an integer",
                ) from exc
            coerced[name] = max(schema.get("min", number), min(schema.get("max", number), number))
        else:
            text = str(value)
            allowed = schema.get("values")
            if allowed and text not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter {name} must be one of {allowed}",
                )
            coerced[name] = text
    return coerced


def _reading_for(device_type: str, power: bool, state: dict[str, Any]) -> dict[str, str]:
    if not power:
        return {"value": "已关闭", "unit": "", "label": "待机"}
    if device_type == "air_conditioner":
        return {"value": str(state.get("temperature", 24)), "unit": "°", "label": "制冷"}
    if device_type == "light":
        return {"value": str(state.get("brightness", 70)), "unit": "%", "label": "亮度"}
    if device_type == "tv":
        return {"value": str(state.get("volume", 30)), "unit": "%", "label": f"{state.get('channel', 1)} 频道"}
    return {"value": "运行中", "unit": "", "label": "在线"}


async def _live_state(device_id: str) -> tuple[dict[str, Any], str | None]:
    catalog = _catalog_or_404(device_id)
    state_data = dict(catalog["defaults"])
    if not _is_connected(device_id):
        return state_data, "Device simulator is not connected"

    response = await hub.get_state(device_id)
    if isinstance(response, dict) and response.get("state"):
        state_data.update(response["state"])
    return state_data, None


async def get_device(device_id: str) -> dict[str, Any]:
    catalog = _catalog_or_404(device_id)
    state_data, message = await _live_state(device_id)
    power = bool(state_data.get("is_on", False))
    return {
        "id": catalog["id"],
        "type": catalog["type"],
        "name": catalog["name"],
        "room": catalog["room"],
        "icon": catalog["icon"],
        "online": _is_connected(device_id),
        "power": power,
        "reading": _reading_for(catalog["type"], power, state_data),
        "state": state_data,
        "capabilities": _capabilities(device_id),
        "energy": catalog["energy"],
        "updated": "刚刚" if _is_connected(device_id) else "未连接",
        "color": catalog["color"],
        "soft": catalog["soft"],
        "glow": catalog["glow"],
        "message": message,
    }


async def list_devices() -> list[dict[str, Any]]:
    return [await get_device(device_id) for device_id in DEVICE_CATALOG]


async def dashboard() -> dict[str, Any]:
    devices = await list_devices()
    online_count = sum(1 for device in devices if device["online"])
    active_count = sum(1 for device in devices if device["power"])
    return {
        "devices": devices,
        "scenes": list_scenes(),
        "summary": {
            "total": len(devices),
            "online": online_count,
            "active": active_count,
            "energy_today": "2.3 kWh",
            "mode": "course-demo",
        },
    }


async def execute_device_command(
    device_id: str,
    command: str,
    params: dict[str, Any] | None = None,
    *,
    source: str = "manual",
) -> dict[str, Any]:
    coerced = _coerce_params(device_id, command, params)
    if not _is_connected(device_id):
        return {
            "success": False,
            "source": source,
            "device_id": device_id,
            "command": command,
            "params": coerced,
            "message": f"{device_id} simulator is not connected",
            "device": await get_device(device_id),
        }

    response = await hub.send_command(device_id, command, coerced)
    success = bool(response.get("success")) if isinstance(response, dict) else False
    return {
        "success": success,
        "source": source,
        "device_id": device_id,
        "command": command,
        "params": coerced,
        "message": response.get("message", "") if isinstance(response, dict) else "Invalid simulator response",
        "state": response.get("state") if isinstance(response, dict) else None,
        "device": await get_device(device_id),
    }


async def execute_batch(commands: list[dict[str, Any]], *, source: str = "batch") -> dict[str, Any]:
    results = []
    for item in commands:
        results.append(
            await execute_device_command(
                item["device_id"],
                item["command"],
                item.get("params", {}),
                source=source,
            )
        )
    return {"success": all(result["success"] for result in results), "results": results}


def list_scenes() -> list[dict[str, Any]]:
    return [
        {
            "id": scene["id"],
            "name": scene["name"],
            "description": scene["description"],
            "actions": scene["commands"],
        }
        for scene in SCENES.values()
    ]


async def execute_scene(scene_id: str) -> dict[str, Any]:
    scene = SCENES.get(scene_id)
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown scene: {scene_id}")
    batch = await execute_batch(scene["commands"], source=f"scene:{scene_id}")
    return {
        "success": batch["success"],
        "scene": {
            "id": scene["id"],
            "name": scene["name"],
            "description": scene["description"],
        },
        "results": batch["results"],
        "devices": await list_devices(),
    }


def _nlu_device_context(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": device["id"],
            "type": device["type"],
            "name": device["name"],
            "room": device["room"],
            "online": device["online"],
            "commands": [
                {"name": capability["name"], "params": capability["params"]}
                for capability in device["capabilities"]
            ],
        }
        for device in devices
    ]


async def call_nlu(text: str, conversation: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    devices = await list_devices()
    payload = {
        "text": text,
        "conversation": conversation or [],
        "devices": _nlu_device_context(devices),
        "scenes": [{"id": scene["id"], "name": scene["name"]} for scene in list_scenes()],
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{AI_SERVICE_BASE_URL}/internal/v1/nlu/interpret", json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI NLU service unavailable: {exc}",
        ) from exc


async def execute_assistant_text(text: str, conversation: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message text is required")

    nlu = await call_nlu(text, conversation)
    results: list[dict[str, Any]] = []
    for action in nlu.get("actions", []):
        if action.get("kind") == "scene":
            results.append({"kind": "scene", **await execute_scene(action["scene_id"])})
        elif action.get("kind") == "device_command":
            results.append({
                "kind": "device_command",
                **await execute_device_command(
                    action["device_id"],
                    action["command"],
                    action.get("params", {}),
                    source="assistant",
                ),
            })

    command_success = all(
        result.get("success", False)
        if result.get("kind") == "device_command"
        else result.get("success", False)
        for result in results
    ) if results else False
    reply = nlu.get("reply") or "我还没有理解这个指令。"
    if nlu.get("understood") and results and not command_success:
        reply = f"{reply} 但有设备尚未连接，请确认模拟器已启动。"

    return {
        "request_id": str(uuid.uuid4()),
        "understood": bool(nlu.get("understood")),
        "text": text,
        "reply": reply,
        "actions": nlu.get("actions", []),
        "results": results,
        "devices": await list_devices(),
    }


async def transcribe_audio(audio: UploadFile, language: str = "zh-CN") -> dict[str, Any]:
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty")

    files = {
        "audio": (
            audio.filename or "recording.wav",
            audio_bytes,
            audio.content_type or "audio/wav",
        )
    }
    data = {"language": language, "request_id": str(uuid.uuid4())}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AI_SERVICE_BASE_URL}/internal/v1/asr/transcriptions",
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI ASR service unavailable: {exc}",
        ) from exc


async def execute_assistant_voice(audio: UploadFile, language: str = "zh-CN") -> dict[str, Any]:
    transcript = await transcribe_audio(audio, language)
    result = await execute_assistant_text(transcript.get("text", ""))
    return {"transcript": transcript, **result}
