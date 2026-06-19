"""NLU 子路由 — LLM + 规则版意图解析模块。

本模块实现 FRONTEND_API_REQUIREMENTS.md §8.2 定义的内部 NLU 接口。
采用双引擎降级策略：
1. 云端引擎 — DeepSeek API（通过 OpenAI 兼容接口）
2. 本地降级 — 规则版 mock 引擎

支持的规则（降级时生效）：
- 单设备控制：打开/关闭 + 设备名
- 参数调节：设备名 + 参数值（温度、亮度、百分比等）
- 多动作：逗号/并/和 连接
- 场景触发：场景名称匹配
- 约束校验：仅使用请求中声明的设备 ID 与命令
"""

import re
import logging
from typing import Any, Literal

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from . import llm_engine

logger = logging.getLogger(__name__)

router = APIRouter()


# ── 数据模型 ──────────────────────────────────────────────────────────────

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


# ── 关键词映射 ────────────────────────────────────────────────────────────

DEVICE_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "light": ("灯", "灯光", "主灯", "氛围灯", "所有灯", "全部灯"),
    "air_conditioner": ("空调",),
    "curtain": ("窗帘",),
    "tv": ("电视",),
    "refrigerator": ("冰箱",),
    "fan": ("风扇",),
}

ROOM_KEYWORDS: tuple[str, ...] = ("客厅", "卧室", "书房", "厨房", "阳台", "主卧")

TURN_ON_WORDS: tuple[str, ...] = ("打开", "开启", "启动", "开灯", "开")
TURN_OFF_WORDS: tuple[str, ...] = ("关闭", "关掉", "关上", "停止", "关")

SCENE_TRIGGER_WORDS: tuple[str, ...] = ("开启", "设置", "进入", "切换到", "执行")

# 数值提取正则
_NUM_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:度|°C|°F|摄氏度|华氏度|档|%|百分之|percent)?"
)
_PERCENT_WORDS = re.compile(r"百分之(\d+)")
_HALF_WORDS = re.compile(r"(一半|半开)")

# 命令关键词映射
_COMMAND_KEYWORDS: dict[str, tuple[str, ...]] = {
    "turn_on": ("打开", "开启", "启动", "开灯", "开"),
    "turn_off": ("关闭", "关掉", "关上", "停止", "关"),
    "set_brightness": ("亮度", "调亮", "调暗", "调到"),
    "set_temperature": ("温度", "调到", "调温"),
    "set_speed": ("档", "速度", "风速"),
    "set_open_percent": ("开", "打开程度", "开一半", "半开"),
    "set_volume": ("音量",),
    "set_channel": ("频道",),
}


# ── NLU 引擎 ─────────────────────────────────────────────────────────────

def _find_device(text: str, devices: list[DeviceInfo]) -> DeviceInfo | None:
    """根据文本匹配设备。

    优先级：
    1. 名称精确匹配
    2. 房间 + 类型匹配（文本中含房间关键词时，只匹配该房间设备）
    3. 类型关键词匹配（文本中无房间关键词时）
    """
    # 检测文本中是否包含房间关键词
    mentioned_room: str | None = None
    for room_kw in ROOM_KEYWORDS:
        if room_kw in text:
            mentioned_room = room_kw
            break

    # 1. 精确名称匹配
    for dev in devices:
        if dev.name in text:
            # 如果文本提到了房间，验证设备房间是否匹配
            if mentioned_room and dev.room and mentioned_room not in (dev.room or ""):
                continue
            return dev

    # 2. 房间 + 类型匹配（仅当文本明确提到房间时）
    if mentioned_room:
        for dev in devices:
            dev_type = dev.type
            keywords = DEVICE_TYPE_KEYWORDS.get(dev_type, ())
            room = dev.room or ""
            if mentioned_room not in room:
                continue
            for kw in keywords:
                if kw in text:
                    return dev
        # 提到了房间但没找到匹配设备 → 返回 None
        return None

    # 3. 类型关键词匹配（无房间关键词时）
    for dev in devices:
        dev_type = dev.type
        keywords = DEVICE_TYPE_KEYWORDS.get(dev_type, ())
        for kw in keywords:
            if kw in text:
                return dev

    return None


def _find_devices_by_type(
    text: str, devices: list[DeviceInfo], dev_type: str
) -> list[DeviceInfo]:
    """查找文本中提到的某类型的所有设备。

    支持"所有灯"、"全部灯"等批量匹配。
    如果文本中提到房间关键词，仅匹配该房间的设备。
    """
    keywords = DEVICE_TYPE_KEYWORDS.get(dev_type, ())
    all_kw = ("所有灯", "全部灯") if dev_type == "light" else ()

    # 检测文本中是否包含房间关键词
    mentioned_room: str | None = None
    for room_kw in ROOM_KEYWORDS:
        if room_kw in text:
            mentioned_room = room_kw
            break

    # 批量匹配（全部灯）
    for kw in all_kw:
        if kw in text:
            return [d for d in devices if d.type == dev_type]

    # 逐个匹配
    matched = []
    for dev in devices:
        if dev.type != dev_type:
            continue
        # 如果文本提到了房间，只匹配该房间的设备
        if mentioned_room and dev.room and mentioned_room not in (dev.room or ""):
            continue
        for kw in keywords:
            if kw in text:
                matched.append(dev)
                break
    return matched


def _extract_number(text: str) -> int | None:
    """从文本中提取数值。"""
    # 处理 "百分之X"
    m = _PERCENT_WORDS.search(text)
    if m:
        return int(m.group(1))

    # 处理 "一半" / "半开"
    if _HALF_WORDS.search(text):
        return 50

    # 通用数值匹配
    m = _NUM_PATTERN.search(text)
    if m:
        try:
            return int(float(m.group(1)))
        except ValueError:
            return None
    return None


def _resolve_command(
    text: str, device: DeviceInfo, number: int | None
) -> tuple[str | None, dict[str, Any]]:
    """根据文本和设备能力解析具体的命令和参数。"""
    available = {c.name: c.params for c in device.commands}

    # 1. 开关
    for w in TURN_ON_WORDS:
        if w in text and "turn_on" in available:
            return "turn_on", {}
    for w in TURN_OFF_WORDS:
        if w in text and "turn_off" in available:
            return "turn_off", {}

    # 2. 亮度调节
    if "set_brightness" in available and number is not None:
        if any(kw in text for kw in ("亮度", "调到", "调亮", "调暗")):
            params = available["set_brightness"]
            lim = params.get("brightness", {})
            v = number
            if isinstance(lim, dict):
                v = max(lim.get("min", 0), min(lim.get("max", 100), v))
            return "set_brightness", {"brightness": v}

    # 3. 温度调节
    if "set_temperature" in available and number is not None:
        if any(kw in text for kw in ("温度", "调到", "调温")):
            params = available["set_temperature"]
            lim = params.get("temperature", {})
            v = number
            if isinstance(lim, dict):
                v = max(lim.get("min", 16), min(lim.get("max", 30), v))
            return "set_temperature", {"temperature": v}

    # 4. 窗帘开度
    if "set_open_percent" in available:
        if number is not None and any(kw in text for kw in ("开", "半开", "一半")):
            params = available["set_open_percent"]
            lim = params.get("percent", {})
            v = number
            if isinstance(lim, dict):
                v = max(lim.get("min", 0), min(lim.get("max", 100), v))
            return "set_open_percent", {"percent": v}

    # 5. 风速/档位
    if "set_speed" in available and number is not None:
        if any(kw in text for kw in ("档", "速度", "风速")):
            return "set_speed", {"speed": number}

    # 6. 默认：有数字用第一个接受数字参数的命令
    if number is not None:
        for cmd_name, params in available.items():
            if cmd_name in ("turn_on", "turn_off"):
                continue
            for pname, plim in params.items():
                if isinstance(plim, dict) and plim.get("type") == "integer":
                    v = number
                    v = max(plim.get("min", 0), min(plim.get("max", 100), v))
                    return cmd_name, {pname: v}

    return None, {}


def _match_scene(text: str, scenes: list[SceneInfo]) -> SceneInfo | None:
    """根据文本匹配场景。"""
    for scene in scenes:
        if scene.name in text:
            return scene
        # 部分匹配
        if scene.id in text.lower():
            return scene
    return None


def _interpret(text: str, devices: list[DeviceInfo], scenes: list[SceneInfo]) -> dict:
    """核心意图解析逻辑。

    Returns:
        dict: 包含 understood, reply, actions 键。
    """
    actions: list[dict] = []
    text_lower = text.lower()

    # ── 场景匹配 ──────────────────────────────────────────────────────
    scene = _match_scene(text, scenes)
    if scene:
        actions.append({"kind": "scene", "scene_id": scene.id})
        return {
            "understood": True,
            "reply": f"好的，正在执行「{scene.name}」场景。",
            "actions": actions,
        }

    # ── 分割复合指令 ──────────────────────────────────────────────────
    # 按 "并" "和" "，" 分割
    parts = re.split(r"[，,并和]+", text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        parts = [text]

    for part in parts:
        number = _extract_number(part)

        # 查找匹配的设备
        device = _find_device(part, devices)
        if device is None:
            # 尝试只匹配类型
            for dtype in DEVICE_TYPE_KEYWORDS:
                matched = _find_devices_by_type(part, devices, dtype)
                if matched:
                    for dev in matched:
                        cmd, params = _resolve_command(part, dev, number)
                        if cmd:
                            actions.append({
                                "kind": "device_command",
                                "device_id": dev.id,
                                "command": cmd,
                                "params": params,
                            })
                    break
            continue

        cmd, params = _resolve_command(part, device, number)
        if cmd is None:
            # 设备找到但无法解析命令 → 不生成动作
            continue

        actions.append({
            "kind": "device_command",
            "device_id": device.id,
            "command": cmd,
            "params": params,
        })

    if not actions:
        return {
            "understood": False,
            "reply": "我还不确定你想控制哪个设备，请告诉我设备名称或房间。",
            "actions": [],
        }

    # 生成回复
    device_names = []
    for a in actions:
        if a["kind"] == "scene":
            device_names.append("场景")
        else:
            for d in devices:
                if d.id == a["device_id"]:
                    device_names.append(d.name)
                    break
            else:
                device_names.append(a["device_id"])

    reply = "好的，正在处理" + "、".join(device_names) + "。"
    return {
        "understood": True,
        "reply": reply,
        "actions": actions,
    }


def _devices_to_dicts(devices: list[DeviceInfo]) -> list[dict]:
    """将 Pydantic 设备模型转为普通 dict（供 LLM 引擎使用）。"""
    return [
        {
            "id": d.id,
            "type": d.type,
            "name": d.name,
            "room": d.room,
            "online": d.online,
            "commands": [{"name": c.name, "params": c.params} for c in d.commands],
        }
        for d in devices
    ]


def _scenes_to_dicts(scenes: list[SceneInfo]) -> list[dict]:
    """将 Pydantic 场景模型转为普通 dict。"""
    return [{"id": s.id, "name": s.name} for s in scenes]


# ── 路由端点 ─────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    """NLU 模块健康检查。"""
    engine = "llm" if llm_engine.llm_available() else "rule"
    return {"status": "ok", "module": "nlu", "engine": engine}


@router.post("/interpret", response_model=InterpretResponse)
async def interpret(request: InterpretRequest = Body(...)):
    """意图解析主端点 — FRONTEND_API_REQUIREMENTS.md §8.2。

    双引擎降级策略：
    1. 优先使用 DeepSeek LLM 进行意图理解
    2. LLM 不可用或解析失败时，降级到本地规则引擎

    约束：
    1. 只能使用请求上下文中存在的设备 ID。
    2. 只能使用设备声明的命令。
    3. 参数必须符合声明的类型。
    4. 无法判断目标时返回 understood=false。
    """
    devices_dict = _devices_to_dicts(request.devices)
    scenes_dict = _scenes_to_dicts(request.scenes)
    conversation_dict = [{"role": m.role, "content": m.content} for m in request.conversation] if request.conversation else []

    # 1. 尝试 LLM 引擎
    if llm_engine.llm_available():
        result = llm_engine.llm_interpret(
            text=request.text,
            devices=devices_dict,
            scenes=scenes_dict,
            conversation=conversation_dict,
        )
        if result is not None:
            logger.info("NLU 使用 LLM 引擎，understood=%s", result["understood"])
            return InterpretResponse(**result)
        logger.info("LLM 引擎失败，降级到规则引擎")

    # 2. 降级到规则引擎
    logger.info("NLU 使用规则引擎")
    result = _interpret(
        text=request.text,
        devices=request.devices,
        scenes=request.scenes,
    )
    return InterpretResponse(**result)


@router.post("/parse")
async def parse(request: InterpretRequest = Body(...)):
    """意图解析端点（旧版兼容）— 复用 /interpret 逻辑。"""
    result = _interpret(
        text=request.text,
        devices=request.devices,
        scenes=request.scenes,
    )
    return result