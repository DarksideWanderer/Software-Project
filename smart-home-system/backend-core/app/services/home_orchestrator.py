from __future__ import annotations

import json
import logging
import os
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException, UploadFile, status

from ..core.device_simulator import hub


AI_SERVICE_BASE_URL = os.getenv("AI_SERVICE_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
TTS_AUDIO_PROXY_PREFIX = "/api/v1/audio/tts"
STATE_PATH = Path(__file__).resolve().parents[2] / "data" / "home_state.json"

logger = logging.getLogger(__name__)


DEVICE_TYPE_META: dict[str, dict[str, Any]] = {
    "air_conditioner": {
        "label": "空调",
        "icon": "icon-ac",
        "color": "#4488a5",
        "soft": "#e0eff5",
        "glow": "rgba(134, 184, 215, .36)",
        "energy": "1.2 kWh",
        "defaults": {"is_on": False, "temperature": 24},
        "commands": {
            "turn_on": {"description": "打开空调", "params": {}},
            "turn_off": {"description": "关闭空调", "params": {}},
            "set_temperature": {
                "description": "设置温度",
                "params": {"temperature": {"type": "integer", "min": 16, "max": 30}},
            },
        },
    },
    "light": {
        "label": "灯",
        "icon": "icon-light",
        "color": "#ad8038",
        "soft": "#f5ead5",
        "glow": "rgba(237, 182, 94, .36)",
        "energy": "0.3 kWh",
        "defaults": {"is_on": False, "brightness": 70, "color": "daylight"},
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
    "tv": {
        "label": "电视",
        "icon": "icon-tv",
        "color": "#7566a0",
        "soft": "#e9e5f3",
        "glow": "rgba(158, 145, 200, .3)",
        "energy": "0.8 kWh",
        "defaults": {"is_on": False, "channel": 1, "volume": 30},
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
    "fridge": {
        "label": "冰箱",
        "icon": "icon-fridge",
        "color": "#4f8f9c",
        "soft": "#dff0f2",
        "glow": "rgba(92, 168, 181, .28)",
        "energy": "1.0 kWh",
        "defaults": {"is_on": True, "temperature": 4},
        "commands": {
            "turn_on": {"description": "打开冰箱", "params": {}},
            "turn_off": {"description": "关闭冰箱", "params": {}},
            "set_temperature": {
                "description": "设置冷藏温度",
                "params": {"temperature": {"type": "integer", "min": 2, "max": 8}},
            },
        },
    },
    "washer": {
        "label": "洗衣机",
        "icon": "icon-settings",
        "color": "#5d7fba",
        "soft": "#e2e8f4",
        "glow": "rgba(103, 132, 190, .28)",
        "energy": "0.9 kWh",
        "defaults": {"is_on": False, "progress": 0},
        "commands": {
            "turn_on": {"description": "启动洗衣机", "params": {}},
            "turn_off": {"description": "停止洗衣机", "params": {}},
            "set_progress": {
                "description": "设置洗涤进度",
                "params": {"progress": {"type": "integer", "min": 0, "max": 100}},
            },
        },
    },
    "water_heater": {
        "label": "热水器",
        "icon": "icon-sun",
        "color": "#b06f45",
        "soft": "#f4e7dc",
        "glow": "rgba(207, 136, 82, .3)",
        "energy": "1.6 kWh",
        "defaults": {"is_on": False, "temperature": 45},
        "commands": {
            "turn_on": {"description": "打开热水器", "params": {}},
            "turn_off": {"description": "关闭热水器", "params": {}},
            "set_temperature": {
                "description": "设置水温",
                "params": {"temperature": {"type": "integer", "min": 35, "max": 65}},
            },
        },
    },
    "air_purifier": {
        "label": "空气净化器",
        "icon": "icon-fan",
        "color": "#5b9b83",
        "soft": "#e0efe9",
        "glow": "rgba(91, 155, 131, .28)",
        "energy": "0.4 kWh",
        "defaults": {"is_on": False, "speed": 1, "air_quality": 42},
        "commands": {
            "turn_on": {"description": "打开净化器", "params": {}},
            "turn_off": {"description": "关闭净化器", "params": {}},
            "set_speed": {
                "description": "设置风速",
                "params": {"speed": {"type": "integer", "min": 1, "max": 5}},
            },
        },
    },
    "curtain": {
        "label": "窗帘",
        "icon": "icon-home",
        "color": "#94745d",
        "soft": "#eee5dd",
        "glow": "rgba(148, 116, 93, .28)",
        "energy": "0.1 kWh",
        "defaults": {"is_on": True, "percent": 100},
        "commands": {
            "turn_on": {"description": "打开窗帘", "params": {}},
            "turn_off": {"description": "关闭窗帘", "params": {}},
            "set_open_percent": {
                "description": "设置开合度",
                "params": {"percent": {"type": "integer", "min": 0, "max": 100}},
            },
        },
    },
    "socket": {
        "label": "智能插座",
        "icon": "icon-settings",
        "color": "#63706b",
        "soft": "#e5e9e7",
        "glow": "rgba(99, 112, 107, .26)",
        "energy": "0.2 kWh",
        "defaults": {"is_on": False},
        "commands": {
            "turn_on": {"description": "打开插座", "params": {}},
            "turn_off": {"description": "关闭插座", "params": {}},
        },
    },
    "robot_vacuum": {
        "label": "扫地机器人",
        "icon": "icon-grid",
        "color": "#6f7d8f",
        "soft": "#e5e9ee",
        "glow": "rgba(111, 125, 143, .28)",
        "energy": "0.5 kWh",
        "defaults": {"is_on": False, "battery": 82},
        "commands": {
            "turn_on": {"description": "开始清扫", "params": {}},
            "turn_off": {"description": "停止清扫", "params": {}},
            "set_battery": {
                "description": "设置电量",
                "params": {"battery": {"type": "integer", "min": 0, "max": 100}},
            },
        },
    },
}

DEVICE_TYPE_CODES = {
    "air_conditioner": "AC",
    "light": "LIGHT",
    "tv": "TV",
    "fridge": "FRIDGE",
    "washer": "WASHER",
    "water_heater": "HEATER",
    "air_purifier": "PURIFIER",
    "curtain": "CURTAIN",
    "socket": "SOCKET",
    "robot_vacuum": "ROBOT",
}


DISCOVERABLE_DEVICES: dict[str, dict[str, Any]] = {
    "ac-001": {"id": "ac-001", "type": "air_conditioner", "original_name": "ac-001", "room": "客厅"},
    "light-001": {"id": "light-001", "type": "light", "original_name": "light-001", "room": "客厅"},
    "tv-001": {"id": "tv-001", "type": "tv", "original_name": "tv-001", "room": "客厅"},
    "fridge-001": {"id": "fridge-001", "type": "fridge", "original_name": "fridge-001", "room": "厨房"},
    "washer-001": {"id": "washer-001", "type": "washer", "original_name": "washer-001", "room": "阳台"},
    "heater-001": {"id": "heater-001", "type": "water_heater", "original_name": "heater-001", "room": "浴室"},
    "purifier-001": {"id": "purifier-001", "type": "air_purifier", "original_name": "purifier-001", "room": "客厅"},
    "curtain-001": {"id": "curtain-001", "type": "curtain", "original_name": "curtain-001", "room": "卧室"},
    "socket-001": {"id": "socket-001", "type": "socket", "original_name": "socket-001", "room": "书房"},
    "robot-001": {"id": "robot-001", "type": "robot_vacuum", "original_name": "robot-001", "room": "全屋"},
}


def _room_for_type(device_type: str) -> str:
    return {
        "air_conditioner": "客厅",
        "light": "客厅",
        "tv": "客厅",
        "fridge": "厨房",
        "washer": "阳台",
        "water_heater": "浴室",
        "air_purifier": "客厅",
        "curtain": "卧室",
        "socket": "书房",
        "robot_vacuum": "全屋",
    }.get(device_type, "未分配")


def _registered_device_info(device_id: str, registered: dict[str, Any]) -> dict[str, Any]:
    device_type = registered.get("type", "socket")
    return {
        "id": device_id,
        "type": device_type,
        "original_name": device_id,
        "room": _room_for_type(device_type),
    }


def _type_from_device_id(device_id: str) -> str | None:
    prefixes = {
        "ac-": "air_conditioner",
        "light-": "light",
        "tv-": "tv",
        "fridge-": "fridge",
        "washer-": "washer",
        "heater-": "water_heater",
        "purifier-": "air_purifier",
        "curtain-": "curtain",
        "socket-": "socket",
        "robot-": "robot_vacuum",
    }
    for prefix, device_type in prefixes.items():
        if device_id.startswith(prefix):
            return device_type
    return None


BUILTIN_SCENES: dict[str, dict[str, Any]] = {
    "home": {
        "id": "home",
        "name": "回家模式",
        "description": "打开客厅主灯和空调。",
        "commands": [
            {"device_id": "light-001", "command": "turn_on", "params": {}},
            {"device_id": "ac-001", "command": "turn_on", "params": {}},
            {"device_id": "ac-001", "command": "set_temperature", "params": {"temperature": 24}},
        ],
        "builtin": True,
    },
    "movie": {
        "id": "movie",
        "name": "观影模式",
        "description": "打开电视，调暗灯光并保持舒适温度。",
        "commands": [
            {"device_id": "tv-001", "command": "turn_on", "params": {}},
            {"device_id": "tv-001", "command": "set_volume", "params": {"volume": 28}},
            {"device_id": "light-001", "command": "turn_on", "params": {}},
            {"device_id": "light-001", "command": "set_brightness", "params": {"brightness": 18}},
            {"device_id": "ac-001", "command": "turn_on", "params": {}},
        ],
        "builtin": True,
    },
    "away": {
        "id": "away",
        "name": "离家模式",
        "description": "关闭已添加的演示设备。",
        "commands": [
            {"device_id": "tv-001", "command": "turn_off", "params": {}},
            {"device_id": "light-001", "command": "turn_off", "params": {}},
            {"device_id": "ac-001", "command": "turn_off", "params": {}},
        ],
        "builtin": True,
    },
}


def _default_state() -> dict[str, Any]:
    return {"bound_devices": {}, "device_states": {}, "user_scenes": {}}


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return _default_state()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to read home state, using empty state")
        return _default_state()
    state = _default_state()
    for key in state:
        if isinstance(data.get(key), dict):
            state[key] = data[key]
    return state


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _catalog_or_404(device_id: str) -> dict[str, Any]:
    state = _load_state()
    bound = state["bound_devices"].get(device_id)
    if bound:
        catalog = DISCOVERABLE_DEVICES.get(device_id, {})
        device_type = bound.get("type") or catalog.get("type") or _type_from_device_id(device_id)
        if device_type:
            return {
                "id": device_id,
                "type": device_type,
                "original_name": bound.get("original_name") or catalog.get("original_name") or device_id,
                "room": bound.get("room") or catalog.get("room") or _room_for_type(device_type),
            }
    device = DISCOVERABLE_DEVICES.get(device_id)
    if device:
        return device
    registered = hub._registry.get(device_id)
    if registered:
        return _registered_device_info(device_id, registered)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown device: {device_id}")


def _meta_for(device_type: str) -> dict[str, Any]:
    return DEVICE_TYPE_META.get(device_type, DEVICE_TYPE_META["socket"])


def _registered_type(device_id: str) -> str | None:
    registered = hub._registry.get(device_id)
    if not registered:
        return None
    return registered.get("type")


def _bound_type(device_id: str, bound: dict[str, Any] | None = None) -> str | None:
    if bound is None:
        state = _load_state()
        bound = state["bound_devices"].get(device_id)
    if not bound:
        return None
    return bound.get("type") or _type_from_device_id(device_id)


def _type_conflict(device_id: str, bound: dict[str, Any] | None = None) -> dict[str, str] | None:
    expected = _bound_type(device_id, bound)
    connected = _registered_type(device_id)
    if expected and connected and expected != connected:
        return {"expected": expected, "connected": connected}
    return None


def _is_connected(device_id: str, expected_type: str | None = None) -> bool:
    if device_id not in hub._devices:
        return False
    connected_type = _registered_type(device_id)
    return not expected_type or not connected_type or connected_type == expected_type


def _bound_or_404(device_id: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or _load_state()
    bound = state["bound_devices"].get(device_id)
    if not bound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device is not bound: {device_id}")
    return bound


def _merged_state(device_id: str, local_state: dict[str, Any], live_state: dict[str, Any] | None) -> dict[str, Any]:
    catalog = _catalog_or_404(device_id)
    meta = _meta_for(catalog["type"])
    merged = {"device_id": device_id, "device_type": catalog["type"], **deepcopy(meta["defaults"])}
    merged.update(local_state or {})
    if live_state:
        merged.update(live_state)
    return merged


async def _live_state(device_id: str, expected_type: str | None = None) -> tuple[dict[str, Any] | None, str | None]:
    connected_type = _registered_type(device_id)
    if expected_type and connected_type and connected_type != expected_type:
        return None, f"Device id conflict: cached type {expected_type}, connected type {connected_type}"
    if not _is_connected(device_id, expected_type):
        return None, "Device simulator is not connected"

    response = await hub.get_state(device_id)
    if isinstance(response, dict) and response.get("state"):
        return response["state"], None
    return None, response.get("message", "Unable to read simulator state") if isinstance(response, dict) else None


def _capabilities(device_id: str) -> list[dict[str, Any]]:
    catalog = _catalog_or_404(device_id)
    meta = _meta_for(catalog["type"])
    return [
        {"name": name, "description": command["description"], "params": command["params"]}
        for name, command in meta["commands"].items()
    ]


def _reading_for(device_type: str, power: bool, state: dict[str, Any]) -> dict[str, str]:
    if not power:
        return {"value": "已关闭", "unit": "", "label": "待机"}
    if "temperature" in state:
        return {"value": str(state.get("temperature")), "unit": "°", "label": "温度"}
    if "brightness" in state:
        return {"value": str(state.get("brightness")), "unit": "%", "label": "亮度"}
    if "volume" in state:
        return {"value": str(state.get("volume")), "unit": "%", "label": f"{state.get('channel', 1)} 频道"}
    if "speed" in state:
        return {"value": str(state.get("speed")), "unit": "档", "label": "风速"}
    if "percent" in state:
        return {"value": str(state.get("percent")), "unit": "%", "label": "开合度"}
    if "battery" in state:
        return {"value": str(state.get("battery")), "unit": "%", "label": "电量"}
    if "progress" in state:
        return {"value": str(state.get("progress")), "unit": "%", "label": "进度"}
    return {"value": "运行中", "unit": "", "label": "在线"}


async def get_device(device_id: str) -> dict[str, Any]:
    state = _load_state()
    bound = _bound_or_404(device_id, state)
    catalog = _catalog_or_404(device_id)
    meta = _meta_for(catalog["type"])
    conflict = _type_conflict(device_id, bound)
    online = _is_connected(device_id, catalog["type"]) and not conflict
    live_state, message = await _live_state(device_id, catalog["type"])
    local_states = state["device_states"]
    state_data = _merged_state(device_id, local_states.get(device_id, {}), live_state)
    if live_state:
        local_states[device_id] = state_data
        _save_state(state)
    power = bool(state_data.get("is_on", False))
    return {
        "id": catalog["id"],
        "type": catalog["type"],
        "type_label": meta["label"],
        "name": bound.get("name") or meta["label"],
        "original_name": catalog["original_name"],
        "room": bound.get("room") or catalog.get("room") or "未分配",
        "icon": meta["icon"],
        "online": online,
        "conflict": bool(conflict),
        "conflict_expected_type": conflict["expected"] if conflict else None,
        "conflict_connected_type": conflict["connected"] if conflict else None,
        "power": power,
        "reading": _reading_for(catalog["type"], power, state_data),
        "state": state_data,
        "capabilities": _capabilities(device_id),
        "energy": meta["energy"],
        "updated": "类型冲突" if conflict else ("刚刚" if online else "离线缓存"),
        "color": meta["color"],
        "soft": meta["soft"],
        "glow": meta["glow"],
        "message": message,
    }


async def list_devices() -> list[dict[str, Any]]:
    state = _load_state()
    return [await get_device(device_id) for device_id in state["bound_devices"]]


def discover_devices() -> list[dict[str, Any]]:
    state = _load_state()
    bound_ids = set(state["bound_devices"])
    candidates = []
    for device_id, registered in hub._registry.items():
        if device_id in bound_ids:
            continue
        device = DISCOVERABLE_DEVICES.get(device_id, _registered_device_info(device_id, registered))
        meta = _meta_for(device["type"])
        candidates.append({
            "id": device_id,
            "type": device["type"],
            "type_code": DEVICE_TYPE_CODES.get(device["type"], device["type"].upper()),
            "type_label": meta["label"],
            "original_name": device["original_name"],
            "room": device.get("room", "未分配"),
            "display": f"{DEVICE_TYPE_CODES.get(device['type'], device['type'].upper())} / {device['original_name']}",
            "online": _is_connected(device_id),
            "bound": False,
        })
    return candidates


def bind_device(device_id: str, name: str | None = None, room: str | None = None) -> dict[str, Any]:
    catalog = _catalog_or_404(device_id)
    state = _load_state()
    if device_id in state["bound_devices"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device is already bound")
    if not _is_connected(device_id, catalog["type"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device is not currently discovered")
    meta = _meta_for(catalog["type"])
    state["bound_devices"][device_id] = {
        "id": device_id,
        "type": catalog["type"],
        "name": name or meta["label"],
        "room": room or catalog.get("room") or "未分配",
        "original_name": catalog["original_name"],
    }
    state["device_states"][device_id] = _merged_state(device_id, {}, None)
    _save_state(state)
    return {"success": True, "device_id": device_id}


def update_bound_device(device_id: str, name: str | None = None, room: str | None = None) -> dict[str, Any]:
    state = _load_state()
    bound = _bound_or_404(device_id, state)
    if name is not None:
        text = name.strip()
        if text:
            bound["name"] = text
    if room is not None:
        text = room.strip()
        if text:
            bound["room"] = text
    state["bound_devices"][device_id] = bound
    _save_state(state)
    return {"success": True, "device_id": device_id}


async def remove_device(device_id: str) -> dict[str, Any]:
    state = _load_state()
    _bound_or_404(device_id, state)
    state["bound_devices"].pop(device_id, None)
    state["device_states"].pop(device_id, None)
    for scene in state["user_scenes"].values():
        scene["commands"] = [cmd for cmd in scene.get("commands", []) if cmd.get("device_id") != device_id]
    _save_state(state)
    return {"success": True, "devices": await list_devices(), "scenes": list_scenes()}


def _coerce_params(device_id: str, command: str, params: dict[str, Any] | None) -> dict[str, Any]:
    meta = _meta_for(_catalog_or_404(device_id)["type"])
    command_meta = meta["commands"].get(command)
    if not command_meta:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{device_id} does not support {command}")
    params = params or {}
    coerced: dict[str, Any] = {}
    for name, schema in command_meta["params"].items():
        if name not in params:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing parameter {name}")
        value = params[name]
        if schema["type"] == "integer":
            try:
                number = int(value)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Parameter {name} must be integer") from exc
            coerced[name] = max(schema.get("min", number), min(schema.get("max", number), number))
        else:
            text = str(value)
            allowed = schema.get("values")
            if allowed and text not in allowed:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Parameter {name} must be one of {allowed}")
            coerced[name] = text
    return coerced


async def execute_device_command(
    device_id: str,
    command: str,
    params: dict[str, Any] | None = None,
    *,
    source: str = "manual",
) -> dict[str, Any]:
    bound = _bound_or_404(device_id)
    catalog = _catalog_or_404(device_id)
    coerced = _coerce_params(device_id, command, params)
    conflict = _type_conflict(device_id, bound)
    if conflict:
        return {
            "success": False,
            "source": source,
            "device_id": device_id,
            "command": command,
            "params": coerced,
            "message": f"{device_id} id conflict: cached type {conflict['expected']}, connected type {conflict['connected']}",
            "device": await get_device(device_id),
        }
    if not _is_connected(device_id, catalog["type"]):
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
    if success and isinstance(response.get("state"), dict):
        state = _load_state()
        state["device_states"][device_id] = _merged_state(device_id, state["device_states"].get(device_id, {}), response["state"])
        _save_state(state)
    message = response.get("message", "") if isinstance(response, dict) else "Invalid simulator response"
    return {
        "success": success,
        "source": source,
        "device_id": device_id,
        "command": command,
        "params": coerced,
        "message": message,
        "device": await get_device(device_id),
    }


async def execute_batch(commands: list[dict[str, Any]], *, source: str = "batch") -> dict[str, Any]:
    results = []
    for item in commands:
        results.append(await execute_device_command(item["device_id"], item["command"], item.get("params", {}), source=source))
    return {"success": all(result["success"] for result in results), "results": results}


def _command_priority(command: str) -> int:
    if command == "turn_on":
        return 0
    if command == "turn_off":
        return 2
    return 1


def plan_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    planned: list[dict[str, Any]] = []
    device_groups: dict[str, list[dict[str, Any]]] = {}
    device_order: list[str] = []

    def flush_device_groups() -> None:
        nonlocal device_groups, device_order
        for device_id in device_order:
            group = device_groups[device_id]
            planned.extend(sorted(group, key=lambda action: _command_priority(action.get("command", ""))))
        device_groups = {}
        device_order = []

    for action in actions:
        if action.get("kind") != "device_command":
            flush_device_groups()
            planned.append(action)
            continue
        device_id = action.get("device_id", "")
        if device_id not in device_groups:
            device_groups[device_id] = []
            device_order.append(device_id)
        device_groups[device_id].append(action)
    flush_device_groups()
    return planned


def list_scenes() -> list[dict[str, Any]]:
    state = _load_state()

    def scene_available(scene: dict[str, Any]) -> bool:
        for cmd in scene.get("commands", []):
            device_id = cmd.get("device_id")
            bound = state["bound_devices"].get(device_id)
            if not bound or _type_conflict(device_id, bound):
                return False
        return True

    scenes = []
    for scene in BUILTIN_SCENES.values():
        item = deepcopy(scene)
        item["available"] = scene_available(item)
        scenes.append(item)
    for scene in state["user_scenes"].values():
        item = deepcopy(scene)
        item["builtin"] = False
        item["available"] = scene_available(item)
        scenes.append(item)
    return scenes


def _scene_or_404(scene_id: str) -> dict[str, Any]:
    state = _load_state()
    if scene_id in state["user_scenes"]:
        return deepcopy(state["user_scenes"][scene_id])
    if scene_id in BUILTIN_SCENES:
        return deepcopy(BUILTIN_SCENES[scene_id])
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown scene: {scene_id}")


def _validate_scene_commands(commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state = _load_state()
    valid = []
    for item in commands:
        device_id = item.get("device_id")
        command = item.get("command")
        bound = state["bound_devices"].get(device_id)
        if not bound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Scene device is not bound: {device_id}")
        conflict = _type_conflict(device_id, bound)
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scene device id conflict: {device_id} cached type {conflict['expected']}, connected type {conflict['connected']}",
            )
        valid.append({"device_id": device_id, "command": command, "params": _coerce_params(device_id, command, item.get("params", {}))})
    return valid


def create_scene(name: str, commands: list[dict[str, Any]], description: str = "") -> dict[str, Any]:
    state = _load_state()
    scene_id = f"user-{uuid.uuid4().hex[:8]}"
    scene = {
        "id": scene_id,
        "name": name.strip() or "自定义场景",
        "description": description.strip(),
        "commands": _validate_scene_commands(commands),
        "builtin": False,
    }
    state["user_scenes"][scene_id] = scene
    _save_state(state)
    return scene


def delete_scene(scene_id: str) -> dict[str, Any]:
    if scene_id in BUILTIN_SCENES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Built-in scenes cannot be deleted")
    state = _load_state()
    if scene_id not in state["user_scenes"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown scene: {scene_id}")
    state["user_scenes"].pop(scene_id)
    _save_state(state)
    return {"success": True, "scenes": list_scenes()}


async def execute_scene(scene_id: str) -> dict[str, Any]:
    scene = _scene_or_404(scene_id)
    batch = await execute_batch(scene.get("commands", []), source=f"scene:{scene_id}")
    return {
        "success": batch["success"],
        "scene": {"id": scene["id"], "name": scene["name"], "description": scene.get("description", "")},
        "results": batch["results"],
        "devices": await list_devices(),
        "scenes": list_scenes(),
    }


async def dashboard() -> dict[str, Any]:
    devices = await list_devices()
    return {
        "devices": devices,
        "candidates": discover_devices(),
        "scenes": list_scenes(),
        "summary": {
            "total": len(devices),
            "online": sum(1 for device in devices if device["online"]),
            "active": sum(1 for device in devices if device["online"] and device["power"]),
            "energy_today": "2.3 kWh",
            "mode": "course-demo",
        },
    }


def _nlu_device_context(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": device["id"],
            "type": device["type"],
            "name": device["name"],
            "room": device["room"],
            "online": device["online"],
            "commands": [{"name": capability["name"], "params": capability["params"]} for capability in device["capabilities"]],
        }
        for device in devices
    ]


async def call_nlu(text: str, conversation: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    devices = await list_devices()
    payload = {
        "text": text,
        "conversation": conversation or [],
        "devices": _nlu_device_context(devices),
        "scenes": [{"id": scene["id"], "name": scene["name"]} for scene in list_scenes() if scene.get("available", True)],
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
            response = await client.post(f"{AI_SERVICE_BASE_URL}/internal/v1/nlu/interpret", json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI NLU service unavailable: {exc}") from exc


async def create_scene_from_text(text: str) -> dict[str, Any]:
    nlu = await call_nlu(text)
    if not nlu.get("understood") or not nlu.get("actions"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=nlu.get("reply") or "Unable to parse scene")
    commands = []
    unsupported = []
    planned_actions = plan_actions(nlu.get("actions", []))
    for action in planned_actions:
        if action.get("kind") == "device_command":
            commands.append({"device_id": action["device_id"], "command": action["command"], "params": action.get("params", {})})
        elif action.get("kind") == "scene":
            unsupported.append(action.get("scene_id", "scene"))
    if unsupported:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Natural language scene cannot include nested scenes: {', '.join(unsupported)}")
    name = text.split("：", 1)[0].split(":", 1)[0].strip() if ("：" in text or ":" in text) else "自然语言场景"
    scene = create_scene(name=name, description=text, commands=commands)
    return {"scene": scene, "nlu": nlu, "scenes": list_scenes()}


def _normalize_tts_speech(tts_response: dict[str, Any]) -> dict[str, Any] | None:
    if tts_response.get("status") != "success":
        return None
    audio_url = tts_response.get("audio_url")
    if not isinstance(audio_url, str) or not audio_url:
        return None
    if audio_url.startswith(("http://", "https://")):
        speech_url = audio_url
    elif audio_url.startswith(("/internal/v1/tts/audio/", "/ai/tts/audio/")):
        speech_url = f"{TTS_AUDIO_PROXY_PREFIX}/{audio_url.rstrip('/').rsplit('/', 1)[-1]}"
    else:
        speech_url = audio_url
    speech = {"url": speech_url, "content_type": tts_response.get("content_type") or "audio/mpeg"}
    if tts_response.get("expires_at"):
        speech["expires_at"] = tts_response["expires_at"]
    return speech


async def synthesize_reply_speech(reply: str) -> dict[str, Any] | None:
    text = reply.strip()
    if not text:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.post(
                f"{AI_SERVICE_BASE_URL}/internal/v1/tts/speech",
                json={"text": text, "voice": "default", "format": "mp3"},
            )
            response.raise_for_status()
            return _normalize_tts_speech(response.json())
    except Exception as exc:
        logger.warning("AI TTS service unavailable: %s", exc)
        return None


async def execute_assistant_text(text: str, conversation: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message text is required")
    nlu = await call_nlu(text, conversation)
    results: list[dict[str, Any]] = []
    planned_actions = plan_actions(nlu.get("actions", []))
    for action in planned_actions:
        if action.get("kind") == "scene":
            results.append({"kind": "scene", **await execute_scene(action["scene_id"])})
        elif action.get("kind") == "device_command":
            results.append({
                "kind": "device_command",
                **await execute_device_command(action["device_id"], action["command"], action.get("params", {}), source="assistant"),
            })
    reply = nlu.get("reply") or "我还没有理解这个指令。"
    speech = await synthesize_reply_speech(reply)
    payload = {
        "request_id": str(uuid.uuid4()),
        "understood": bool(nlu.get("understood")),
        "text": text,
        "reply": reply,
        "actions": planned_actions,
        "results": results,
        "devices": await list_devices(),
        "scenes": list_scenes(),
    }
    if speech:
        payload["speech"] = speech
    return payload


async def transcribe_audio(audio: UploadFile, language: str = "zh-CN") -> dict[str, Any]:
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty")
    files = {"audio": (audio.filename or "recording.wav", audio_bytes, audio.content_type or "audio/wav")}
    data = {"language": language, "request_id": str(uuid.uuid4())}
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.post(f"{AI_SERVICE_BASE_URL}/internal/v1/asr/transcriptions", files=files, data=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        body = ""
        if hasattr(exc, "response") and exc.response is not None:
            try:
                body = exc.response.text[:500]
            except Exception:
                body = "(unable to read response body)"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI ASR service unavailable: {exc}. Response body: {body}") from exc


async def execute_assistant_voice(audio: UploadFile, language: str = "zh-CN") -> dict[str, Any]:
    transcript = await transcribe_audio(audio, language)
    result = await execute_assistant_text(transcript.get("text", ""))
    return {"transcript": transcript, **result}
