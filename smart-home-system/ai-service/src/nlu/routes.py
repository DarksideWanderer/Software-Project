"""NLU 子路由 — 规则版 mock 意图解析模块。

本模块实现 FRONTEND_API_REQUIREMENTS.md §8.2 定义的内部 NLU 接口。
当前版本不调用真实大模型，只基于请求中的 devices/scenes 生成受约束动作计划。
"""

import re
from typing import Any, Literal

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

router = APIRouter()


class ConversationMessage(BaseModel):
    role: str | None = None
    content: str | None = None


class DeviceCommand(BaseModel):
    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class DeviceInfo(BaseModel):
    id: str
    type: str
    name: str
    room: str | None = None
    online: bool = True
    commands: list[DeviceCommand] = Field(default_factory=list)


class SceneInfo(BaseModel):
    id: str
    name: str


class InterpretRequest(BaseModel):
    text: str = ""
    conversation: list[ConversationMessage] = Field(default_factory=list)
    devices: list[DeviceInfo] = Field(default_factory=list)
    scenes: list[SceneInfo] = Field(default_factory=list)


class DeviceAction(BaseModel):
    kind: Literal["device_command"] = "device_command"
    device_id: str
    command: str
    params: dict[str, Any] = Field(default_factory=dict)


class SceneAction(BaseModel):
    kind: Literal["scene"] = "scene"
    scene_id: str


Action = DeviceAction | SceneAction


class InterpretResponse(BaseModel):
    understood: bool
    reply: str
    actions: list[Action] = Field(default_factory=list)


DEVICE_KEYWORDS = {
    "light": ("灯", "灯光", "主灯", "氛围灯"),
    "air_conditioner": ("空调",),
    "curtain": ("窗帘",),
}

ROOM_KEYWORDS = ("客厅", "卧室", "书房", "厨房", "阳台")


TURN_ON_WORDS = ("打开", "开启", "启动", "开灯")
TURN_OFF_WORDS = ("关闭", "关掉", "关上", "停止")


@router.get("/health")
async def health():
    """NLU 模块健康检查。"""
    return {"status": "ok", "module": "nlu"}


@router.post("/interpret", response_model=InterpretResponse)
async def interpret(request: InterpretRequest) -> InterpretResponse:
    """文档主接口：生成受约束的设备/场景动作计划。"""
    return interpret_mock(request)


@router.post("/parse", response_model=InterpretResponse)
async def parse_legacy(
    request: InterpretRequest = Body(default_factory=InterpretRequest),
) -> InterpretResponse:
    """旧版兼容端点，复用 /interpret 的 mock 解析逻辑。"""
    return interpret_mock(request)


def interpret_mock(request: InterpretRequest) -> InterpretResponse:
    text = _normalize(request.text)
    if not text:
        return InterpretResponse(understood=False, reply="请提供需要解析的指令。")

    scene_response = _try_parse_scene(text, request.scenes)
    if scene_response:
        return scene_response

    actions: list[Action] = []
    messages: list[str] = []

    for device_type in ("light", "air_conditioner", "curtain"):
        if not _mentions_device_type(text, device_type):
            continue
        devices = _candidate_devices(text, request.devices, device_type)
        if not devices:
            return InterpretResponse(
                understood=False,
                reply=f"没有找到可用的{_device_label(device_type)}，请确认设备是否在线或已接入。",
            )
        if len(devices) > 1:
            return InterpretResponse(
                understood=False,
                reply=f"请说明要操作哪个房间的{_device_label(device_type)}。",
            )

        device = devices[0]
        device_actions = _actions_for_device(text, device)
        if not device_actions:
            return InterpretResponse(
                understood=False,
                reply=f"{device.name}不支持该指令，或缺少必要参数。",
            )
        actions.extend(device_actions)
        messages.extend(_describe_action(device, action) for action in device_actions)

    if not actions:
        return InterpretResponse(
            understood=False,
            reply="暂时无法理解该指令，请尝试设备控制或场景模式。",
        )

    return InterpretResponse(
        understood=True,
        reply=f"好的，已生成计划：{'，'.join(messages)}。",
        actions=actions,
    )


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


def _try_parse_scene(text: str, scenes: list[SceneInfo]) -> InterpretResponse | None:
    if "模式" not in text and not any(word in text for word in ("场景", "观影", "睡眠", "回家", "离家")):
        return None
    for scene in scenes:
        if scene.name in text or scene.id in text:
            return InterpretResponse(
                understood=True,
                reply=f"好的，已生成{scene.name}场景执行计划。",
                actions=[SceneAction(scene_id=scene.id)],
            )
    return InterpretResponse(
        understood=False,
        reply="没有找到匹配的场景，请确认场景是否已配置。",
    )


def _mentions_device_type(text: str, device_type: str) -> bool:
    return any(keyword in text for keyword in DEVICE_KEYWORDS.get(device_type, ()))


def _candidate_devices(
    text: str, devices: list[DeviceInfo], device_type: str
) -> list[DeviceInfo]:
    same_type = [device for device in devices if device.online and device.type == device_type]
    if not same_type:
        return []

    named = [device for device in same_type if device.name and device.name in text]
    if named:
        return named

    room_words = {device.room for device in same_type if device.room}
    mentioned_rooms = [room for room in room_words if room and room in text]
    if mentioned_rooms:
        return [device for device in same_type if device.room in mentioned_rooms]
    if any(room in text for room in ROOM_KEYWORDS):
        return []

    return same_type if len(same_type) == 1 else []


def _actions_for_device(text: str, device: DeviceInfo) -> list[DeviceAction]:
    supported = {command.name: command for command in device.commands}
    actions: list[DeviceAction] = []

    if device.type == "light":
        if any(word in text for word in TURN_ON_WORDS):
            _append_action(actions, device, supported, "turn_on", {})
        if any(word in text for word in TURN_OFF_WORDS):
            _append_action(actions, device, supported, "turn_off", {})
        brightness = _extract_number(text, keywords=("亮度", "百分之", "%"))
        if brightness is not None:
            _append_action(
                actions,
                device,
                supported,
                "set_brightness",
                {"brightness": brightness},
            )

    if device.type == "air_conditioner":
        temperature = _extract_number(text, keywords=("温度", "调到", "设为", "度"))
        if temperature is None and any(word in text for word in TURN_ON_WORDS):
            _append_action(actions, device, supported, "turn_on", {})
        if temperature is None and any(word in text for word in TURN_OFF_WORDS):
            _append_action(actions, device, supported, "turn_off", {})
        if temperature is not None:
            _append_action(
                actions,
                device,
                supported,
                "set_temperature",
                {"temperature": temperature},
            )

    if device.type == "curtain":
        if any(word in text for word in ("打开", "开启", "拉开")):
            _append_action(actions, device, supported, "open", {})
        if any(word in text for word in ("关闭", "关上", "合上")):
            _append_action(actions, device, supported, "close", {})
        open_percent = 50 if any(word in text for word in ("一半", "半开")) else _extract_number(
            text, keywords=("开到", "打开到", "开合", "%", "百分之")
        )
        if open_percent is not None:
            _append_action(
                actions,
                device,
                supported,
                "set_open_percent",
                {"percent": open_percent},
            )

    return actions


def _append_action(
    actions: list[DeviceAction],
    device: DeviceInfo,
    supported: dict[str, DeviceCommand],
    command_name: str,
    params: dict[str, Any],
) -> None:
    command = supported.get(command_name)
    if not command:
        return
    if not _params_allowed(params, command.params):
        return
    actions.append(
        DeviceAction(device_id=device.id, command=command_name, params=params)
    )


def _params_allowed(params: dict[str, Any], schema: dict[str, Any]) -> bool:
    for name, value in params.items():
        rule = schema.get(name)
        if not isinstance(rule, dict):
            return False
        if rule.get("type") == "integer" and not isinstance(value, int):
            return False
        min_value = rule.get("min")
        max_value = rule.get("max")
        if min_value is not None and value < min_value:
            return False
        if max_value is not None and value > max_value:
            return False
    return True


def _extract_number(text: str, keywords: tuple[str, ...]) -> int | None:
    if not any(keyword in text for keyword in keywords):
        return None
    match = re.search(r"\d+", text)
    if match:
        return int(match.group())
    chinese_numbers = {
        "一半": 50,
        "半": 50,
        "零": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
        "二十": 20,
        "二十一": 21,
        "二十二": 22,
        "二十三": 23,
        "二十四": 24,
        "二十五": 25,
        "二十六": 26,
        "二十七": 27,
        "二十八": 28,
        "二十九": 29,
        "三十": 30,
        "五十": 50,
        "八十": 80,
    }
    for word, value in sorted(chinese_numbers.items(), key=lambda item: len(item[0]), reverse=True):
        if word in text:
            return value
    return None


def _describe_action(device: DeviceInfo, action: DeviceAction) -> str:
    if action.command == "turn_on":
        return f"打开{device.name}"
    if action.command == "turn_off":
        return f"关闭{device.name}"
    if action.command == "set_temperature":
        return f"将{device.name}温度设为{action.params.get('temperature')}度"
    if action.command == "set_brightness":
        return f"将{device.name}亮度设为{action.params.get('brightness')}%"
    if action.command == "open":
        return f"打开{device.name}"
    if action.command == "close":
        return f"关闭{device.name}"
    if action.command == "set_open_percent":
        return f"将{device.name}开合比例设为{action.params.get('percent')}%"
    return f"执行{device.name}的{action.command}"


def _device_label(device_type: str) -> str:
    return {
        "light": "灯光",
        "air_conditioner": "空调",
        "curtain": "窗帘",
    }.get(device_type, "设备")
