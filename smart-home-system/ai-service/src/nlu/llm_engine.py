"""NLU LLM 引擎 — 基于 DeepSeek API 的意图解析

使用 OpenAI 兼容接口调用 DeepSeek 大模型，将自然语言指令
解析为受约束的设备动作计划。

约束：
1. 只能使用请求上下文中存在的设备 ID。
2. 只能使用设备声明的命令。
3. 参数必须符合声明的类型和范围。
4. LLM 失败时自动降级到规则引擎。
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ── DeepSeek API 配置 ────────────────────────────────────────────────────
DEEPSEEK_BASE_URL = os.environ.get(
    "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
)
DEEPSEEK_API_KEY = os.environ.get("LLM_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("NLU_MODEL", "deepseek-chat")

# 超时与重试
LLM_TIMEOUT_SECONDS = 15
LLM_MAX_TOKENS = 1024


# ── Prompt 构建 ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """你是一个智能家居语音助手。用户会用中文说出控制指令，你需要将其解析为结构化的设备动作。

## 可用设备
{devices_json}

## 可用场景
{scenes_json}

## 输出格式
你必须只返回一个 JSON 对象，格式如下：
```json
{{
  "understood": true/false,
  "reply": "对用户的简短中文回复",
  "actions": [
    {{
      "kind": "device_command",
      "device_id": "设备ID",
      "command": "命令名",
      "params": {{}}
    }},
    {{
      "kind": "scene",
      "scene_id": "场景ID"
    }}
  ]
}}
```

## 规则
1. device_id 必须来自上面列出的可用设备。
2. command 必须是该设备声明的命令之一。
3. params 的值必须符合该命令参数的类型和范围。
4. 如果用户说的是场景（如"观影模式"），使用 scene 类型的 action。
5. 如果无法确定用户意图，设置 understood=false 并让用户补充信息。
6. 不要在 reply 中说"根据你的要求"之类的套话，直接说执行结果。
7. 多设备指令可以包含多个 actions。
8. 参数中的数字直接使用 JSON number，不要用字符串。

## 示例
用户："打开客厅灯"
```json
{{"understood":true,"reply":"已打开客厅主灯。","actions":[{{"kind":"device_command","device_id":"light-living-001","command":"turn_on","params":{{}}}}]}}
```

用户："把空调调到22度"
```json
{{"understood":true,"reply":"客厅空调已调到22°C。","actions":[{{"kind":"device_command","device_id":"ac-living-001","command":"set_temperature","params":{{"temperature":22}}}}]}}
```

用户："弄一下那个东西"
```json
{{"understood":false,"reply":"我还不确定你想控制哪个设备，请告诉我设备名称或房间。","actions":[]}}
```"""


def _build_devices_json(devices: list[dict]) -> str:
    """将设备列表转为 LLM 友好的 JSON 描述。"""
    simplified = []
    for d in devices:
        item = {
            "id": d.get("id"),
            "type": d.get("type"),
            "name": d.get("name"),
            "room": d.get("room"),
            "online": d.get("online", True),
            "commands": [],
        }
        for cmd in d.get("commands", []):
            cmd_info = {"name": cmd["name"]}
            if cmd.get("params"):
                cmd_info["params"] = cmd["params"]
            item["commands"].append(cmd_info)
        simplified.append(item)
    return json.dumps(simplified, ensure_ascii=False, indent=2)


def _build_scenes_json(scenes: list[dict]) -> str:
    """将场景列表转为 LLM 友好的 JSON 描述。"""
    simplified = [{"id": s.get("id"), "name": s.get("name")} for s in scenes]
    return json.dumps(simplified, ensure_ascii=False, indent=2)


def _build_user_prompt(text: str) -> str:
    """构建用户消息。"""
    return f"用户指令：{text}"


def _extract_json(text: str) -> dict | None:
    """从 LLM 返回的文本中提取 JSON 对象。"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 代码块
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass

    # 尝试提取 ``` ... ``` 代码块
    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass

    # 尝试找到第一个 { 和最后一个 }
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass

    return None


def _validate_actions(
    actions: list[dict], devices: list[dict], scenes: list[dict]
) -> list[dict]:
    """校验并清洗 LLM 返回的 actions。

    只保留合法的设备 ID、命令和参数。
    """
    device_ids = {d["id"] for d in devices}
    device_commands: dict[str, set[str]] = {}
    device_cmd_params: dict[str, dict[str, dict]] = {}
    for d in devices:
        did = d["id"]
        cmds = set()
        params_map = {}
        for cmd in d.get("commands", []):
            cmds.add(cmd["name"])
            if cmd.get("params"):
                params_map[cmd["name"]] = cmd["params"]
        device_commands[did] = cmds
        device_cmd_params[did] = params_map

    scene_ids = {s["id"] for s in scenes}

    valid: list[dict] = []
    for action in actions:
        kind = action.get("kind", "")

        if kind == "scene":
            sid = action.get("scene_id", "")
            if sid in scene_ids:
                valid.append({"kind": "scene", "scene_id": sid})
            continue

        if kind == "device_command":
            did = action.get("device_id", "")
            cmd = action.get("command", "")
            params = action.get("params", {})

            if did not in device_ids:
                logger.warning("LLM 使用了未知设备 ID: %s", did)
                continue
            if cmd not in device_commands.get(did, set()):
                logger.warning("LLM 对设备 %s 使用了不支持的命令: %s", did, cmd)
                continue

            # 校验参数
            valid_params: dict[str, Any] = {}
            allowed_params = device_cmd_params.get(did, {}).get(cmd, {})
            for pname, pvalue in params.items():
                if pname not in allowed_params:
                    continue
                pinfo = allowed_params[pname]
                if not isinstance(pinfo, dict):
                    valid_params[pname] = pvalue
                    continue
                # 类型校验 & 范围裁剪
                ptype = pinfo.get("type", "")
                try:
                    if ptype == "integer":
                        v = int(pvalue)
                        v = max(pinfo.get("min", v), min(pinfo.get("max", v), v))
                        valid_params[pname] = v
                    elif ptype == "boolean":
                        valid_params[pname] = bool(pvalue)
                    else:
                        valid_params[pname] = pvalue
                except (ValueError, TypeError):
                    continue

            valid.append({
                "kind": "device_command",
                "device_id": did,
                "command": cmd,
                "params": valid_params,
            })

    return valid


# ── 公开接口 ────────────────────────────────────────────────────────────

def llm_interpret(
    text: str,
    devices: list[dict],
    scenes: list[dict],
    conversation: list[dict] | None = None,
) -> dict | None:
    """使用 DeepSeek LLM 进行意图解析。

    Args:
        text: 用户输入的自然语言文本。
        devices: 可用设备列表。
        scenes: 可用场景列表。
        conversation: 历史对话（可选）。

    Returns:
        成功时返回 {understood, reply, actions}；
        LLM 不可用或解析失败时返回 None（调用方应降级到规则引擎）。
    """
    if not DEEPSEEK_API_KEY:
        logger.info("未配置 LLM_API_KEY，跳过 LLM NLU")
        return None

    try:
        import urllib.request
        import urllib.error

        system_prompt = _SYSTEM_PROMPT.format(
            devices_json=_build_devices_json(devices),
            scenes_json=_build_scenes_json(scenes),
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if conversation:
            for msg in conversation[-6:]:  # 最多 6 条历史
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": _build_user_prompt(text)})

        body = json.dumps({
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "max_tokens": LLM_MAX_TOKENS,
            "temperature": 0.1,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            },
        )

        resp = urllib.request.urlopen(req, timeout=LLM_TIMEOUT_SECONDS)
        data = json.loads(resp.read().decode())

        if "choices" not in data or not data["choices"]:
            logger.warning("LLM 返回空 choices")
            return None

        content = data["choices"][0]["message"]["content"]
        logger.debug("LLM 原始响应: %s", content[:300])

        parsed = _extract_json(content)
        if not parsed:
            logger.warning("无法从 LLM 响应中提取 JSON")
            return None

        understood = parsed.get("understood", False)
        reply = parsed.get("reply", "")
        raw_actions = parsed.get("actions", [])

        # 校验 actions
        actions = _validate_actions(raw_actions, devices, scenes)

        if not understood and not actions:
            return {
                "understood": False,
                "reply": reply or "我还不确定你想控制哪个设备，请告诉我设备名称或房间。",
                "actions": [],
            }

        if not actions:
            logger.warning("LLM 返回 understood=true 但 actions 校验后为空")
            return None

        return {
            "understood": understood,
            "reply": reply,
            "actions": actions,
        }

    except urllib.error.HTTPError as e:
        logger.warning("DeepSeek API HTTP 错误: %s %s", e.code, e.reason)
        return None
    except Exception as e:
        logger.warning("LLM NLU 调用失败: %s", e)
        return None


def llm_available() -> bool:
    """检查 LLM 引擎是否可用。"""
    return bool(DEEPSEEK_API_KEY)
