import json

import httpx
from pydantic import ValidationError

from .config import Settings
from .schemas import NluContext, NluResponse, Slots


SYSTEM_PROMPT = """你是智能家居语音交互助手系统的NLU模块。
你的任务是把用户中文指令解析为严格JSON，不要输出Markdown、解释或额外文本。
你只负责语义解析，不控制设备，不访问数据库，不调用外部家电。

允许的intent:
- device_control
- device_query
- weather_query
- reminder_create
- scene_mode
- unknown

允许的action:
- turn_on
- turn_off
- set_temperature
- increase_temperature
- decrease_temperature
- set_brightness
- increase_brightness
- decrease_brightness
- open
- close
- set_open_percent
- query_status

设备类型:
- light
- air_conditioner
- curtain

位置:
- living_room
- bedroom
- study
- kitchen
- balcony

输出JSON字段必须为:
{
  "success": true,
  "intent": "...",
  "confidence": 0.0到1.0,
  "slots": {
    "device_type": null或字符串,
    "location": null或字符串,
    "action": null或字符串,
    "value": null或数字或字符串,
    "unit": null或字符串,
    "city": null或字符串,
    "datetime": null或字符串,
    "content": null或字符串
  },
  "need_clarification": false,
  "reply": "简短中文回复"
}

如果缺少执行所需参数，need_clarification必须为true，reply写成一句追问。
如果无法理解，intent为unknown，confidence低于0.5。"""


def is_deepseek_configured() -> bool:
    return bool(Settings().deepseek_api_key)


def parse_with_deepseek(text: str, context: NluContext | None = None) -> NluResponse:
    settings = Settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("DeepSeek API key is not configured.")

    response = httpx.post(
        f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.deepseek_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "text": text,
                            "context": context.model_dump() if context else None,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=15,
    )
    response.raise_for_status()

    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    return parse_deepseek_content(content)


def parse_deepseek_content(content: str) -> NluResponse:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("DeepSeek returned invalid JSON.") from exc

    data.setdefault("success", True)
    data.setdefault("confidence", 0.6)
    data.setdefault("slots", {})
    data.setdefault("need_clarification", False)
    data.setdefault("reply", "已完成语义解析。")
    data["slots"] = Slots(**data["slots"]).model_dump()

    try:
        return NluResponse(**data)
    except ValidationError as exc:
        raise ValueError("DeepSeek JSON does not match NLU schema.") from exc
