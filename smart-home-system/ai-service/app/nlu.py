import re

from .schemas import NluContext, NluResponse, Slots


LOCATION_KEYWORDS = {
    "客厅": "living_room",
    "卧室": "bedroom",
    "书房": "study",
    "厨房": "kitchen",
    "阳台": "balcony",
}

CITY_KEYWORDS = [
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "南京",
    "苏州",
    "成都",
    "武汉",
    "西安",
]

SUPPORTED_ACTIONS = [
    "turn_on",
    "turn_off",
    "set_temperature",
    "increase_temperature",
    "decrease_temperature",
    "set_brightness",
    "increase_brightness",
    "decrease_brightness",
    "open",
    "close",
    "set_open_percent",
    "query_status",
]

SUPPORTED_INTENTS = [
    "device_control",
    "device_query",
    "weather_query",
    "reminder_create",
    "scene_mode",
    "unknown",
]


def parse_text(text: str, context: NluContext | None = None) -> NluResponse:
    normalized = _normalize(text)
    context = context or NluContext()

    if _is_weather_query(normalized):
        return _parse_weather(normalized)
    if _is_reminder_create(normalized):
        return _parse_reminder(normalized)
    if _is_scene_mode(normalized):
        return NluResponse(
            success=True,
            intent="scene_mode",
            confidence=0.8,
            slots=Slots(),
            need_clarification=False,
            reply="已识别为场景模式，当前版本暂不自动执行场景。",
        )

    device_type = _extract_device_type(normalized, context)
    if device_type:
        return _parse_device_command(normalized, device_type, context)

    return NluResponse(
        success=True,
        intent="unknown",
        confidence=0.3,
        slots=Slots(),
        need_clarification=False,
        reply="暂时无法理解该指令，请尝试设备控制、天气查询或提醒创建。",
    )


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


def _extract_device_type(text: str, context: NluContext) -> str | None:
    if "空调" in text:
        return "air_conditioner"
    if "窗帘" in text:
        return "curtain"
    if "灯光" in text or "灯" in text:
        return "light"
    return context.last_device_type


def _extract_location(text: str, context: NluContext) -> str | None:
    for keyword, location in LOCATION_KEYWORDS.items():
        if keyword in text:
            return location
    return context.last_location


def _extract_city(text: str) -> str | None:
    for city in CITY_KEYWORDS:
        if city in text:
            return city
    match = re.search(r"([\u4e00-\u9fa5]{2,4})(?:天气|会下雨|下雨|气温)", text)
    if not match:
        return None
    candidate = match.group(1)
    for prefix in ("今天", "明天", "后天", "查询", "看看"):
        candidate = candidate.replace(prefix, "")
    return candidate or None


def _extract_first_number(text: str) -> int | None:
    match = re.search(r"\d+", text)
    if match:
        return int(match.group())
    chinese_numbers = {
        "十六": 16,
        "十七": 17,
        "十八": 18,
        "十九": 19,
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
        "一半": 50,
        "半": 50,
    }
    for keyword, value in chinese_numbers.items():
        if keyword in text:
            return value
    return None


def _is_weather_query(text: str) -> bool:
    return any(keyword in text for keyword in ("天气", "下雨", "气温")) and "空调" not in text


def _parse_weather(text: str) -> NluResponse:
    city = _extract_city(text)
    return NluResponse(
        success=True,
        intent="weather_query",
        confidence=0.88,
        slots=Slots(city=city),
        need_clarification=city is None,
        reply=f"正在查询{city}天气。" if city else "你想查询哪个城市的天气？",
    )


def _is_reminder_create(text: str) -> bool:
    return "提醒" in text or "叫我" in text


def _parse_reminder(text: str) -> NluResponse:
    datetime_text = _extract_datetime_text(text)
    content = _extract_reminder_content(text, datetime_text)
    need_clarification = not datetime_text or not content
    return NluResponse(
        success=True,
        intent="reminder_create",
        confidence=0.86,
        slots=Slots(datetime=datetime_text, content=content),
        need_clarification=need_clarification,
        reply=(
            f"好的，已识别提醒：{datetime_text}，{content}。"
            if not need_clarification
            else "请补充提醒时间和提醒内容。"
        ),
    )


def _extract_datetime_text(text: str) -> str | None:
    patterns = [
        r"(今天|明天|后天)?(早上|上午|中午|下午|晚上|今晚)?[一二三四五六七八九十\d]+点(半)?",
        r"\d+分钟后",
        r"[一二三四五六七八九十]+分钟后",
        r"\d+小时后",
        r"[一二三四五六七八九十]+小时后",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


def _extract_reminder_content(text: str, datetime_text: str | None) -> str | None:
    content = text
    for token in ("提醒我", "提醒", "叫我"):
        content = content.replace(token, "")
    if datetime_text:
        content = content.replace(datetime_text, "")
    content = content.strip("，。,. ")
    return content or None


def _is_scene_mode(text: str) -> bool:
    return "模式" in text and any(keyword in text for keyword in ("回家", "睡眠", "观影", "离家"))


def _parse_device_command(text: str, device_type: str, context: NluContext) -> NluResponse:
    location = _extract_location(text, context)
    action, value, unit = _extract_action(text, device_type)
    intent = "device_query" if action == "query_status" else "device_control"

    if not location and _needs_location(text, device_type):
        return NluResponse(
            success=True,
            intent=intent,
            confidence=0.72,
            slots=Slots(device_type=device_type, action=action, value=value, unit=unit),
            need_clarification=True,
            reply=f"你想操作哪个房间的{_device_name(device_type)}？",
        )

    if action is None:
        return NluResponse(
            success=True,
            intent="unknown",
            confidence=0.45,
            slots=Slots(device_type=device_type, location=location),
            need_clarification=True,
            reply=f"你想对{_device_name(device_type)}执行什么操作？",
        )

    return NluResponse(
        success=True,
        intent=intent,
        confidence=0.9,
        slots=Slots(
            device_type=device_type,
            location=location,
            action=action,
            value=value,
            unit=unit,
        ),
        need_clarification=False,
        reply=_build_device_reply(device_type, location, action, value, unit, intent),
    )


def _extract_action(text: str, device_type: str) -> tuple[str | None, int | None, str | None]:
    number = _extract_first_number(text)
    if any(keyword in text for keyword in ("状态", "查询", "怎么样", "开着", "关着")):
        return "query_status", None, None
    if device_type == "air_conditioner":
        if any(keyword in text for keyword in ("调到", "设置", "设为")) and number is not None:
            return "set_temperature", number, "celsius"
        if any(keyword in text for keyword in ("升高", "调高", "增加")):
            return "increase_temperature", number, "celsius"
        if any(keyword in text for keyword in ("降低", "调低", "减少")):
            return "decrease_temperature", number, "celsius"
    if device_type == "light":
        if any(keyword in text for keyword in ("亮度", "调亮", "调暗")) and number is not None:
            return "set_brightness", number, "percent"
        if any(keyword in text for keyword in ("调亮", "增加亮度")):
            return "increase_brightness", number, "percent"
        if any(keyword in text for keyword in ("调暗", "降低亮度")):
            return "decrease_brightness", number, "percent"
    if device_type == "curtain":
        if any(keyword in text for keyword in ("一半", "半开")):
            return "set_open_percent", 50, "percent"
        if any(keyword in text for keyword in ("开到", "打开到", "开合")) and number is not None:
            return "set_open_percent", number, "percent"
        if any(keyword in text for keyword in ("打开", "开启", "拉开")):
            return "open", None, None
        if any(keyword in text for keyword in ("关闭", "关上", "合上")):
            return "close", None, None
    if any(keyword in text for keyword in ("打开", "开启", "启动")):
        return "turn_on", None, None
    if any(keyword in text for keyword in ("关闭", "关掉", "关上", "停止")):
        return "turn_off", None, None
    return None, number, None


def _needs_location(text: str, device_type: str) -> bool:
    return device_type in {"light", "air_conditioner", "curtain"} and not any(
        keyword in text for keyword in ("所有", "全部")
    )


def _device_name(device_type: str) -> str:
    return {
        "light": "灯",
        "air_conditioner": "空调",
        "curtain": "窗帘",
    }.get(device_type, "设备")


def _location_name(location: str | None) -> str:
    if location is None:
        return ""
    for chinese, code in LOCATION_KEYWORDS.items():
        if code == location:
            return chinese
    return location


def _build_device_reply(
    device_type: str,
    location: str | None,
    action: str,
    value: int | None,
    unit: str | None,
    intent: str,
) -> str:
    target = f"{_location_name(location)}{_device_name(device_type)}"
    if intent == "device_query":
        return f"好的，已识别为查询{target}状态。"
    if value is not None and unit == "celsius":
        return f"好的，已识别为将{target}设置为{value}度。"
    if value is not None and unit == "percent":
        return f"好的，已识别为将{target}设置为{value}%。"
    action_text = {
        "turn_on": "打开",
        "turn_off": "关闭",
        "open": "打开",
        "close": "关闭",
    }.get(action, action)
    return f"好的，已识别为{action_text}{target}。"
