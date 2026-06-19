#!/usr/bin/env python3
"""AI Service 端到端测试脚本

验证完整流水线：
1. 健康检查 — /internal/health
2. ASR 转写 — /internal/v1/asr/transcriptions (mock)
3. NLU 意图解析 — /internal/v1/nlu/interpret (LLM + 规则降级)
4. TTS 语音合成 — /internal/v1/tts/speech (pyttsx3 本地)

用法:
    cd smart-home-system/ai-service
    python scripts/e2e_test.py
"""

import io
import json
import sys
import time
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8001"

# ── 测试用例 ─────────────────────────────────────────────────────────────

TEST_CASES = [
    # (name, text, expected_device, expected_command)
    ("单设备开关", "打开客厅灯", "light-living-001", "turn_on"),
    ("温度调节", "把空调调到26度", "ac-living-001", "set_temperature"),
    ("复合指令", "打开电视并把客厅灯调到50%", None, None),  # 多动作
    ("场景触发", "开启观影模式", None, None),
    ("模糊指令", "弄一下那个东西", None, None),  # understood=false 预期
]

# ── 测试设备（与 docs/FRONTEND_API_REQUIREMENTS.md §4.3 一致）────────────

TEST_DEVICES = [
    {
        "id": "ac-living-001", "type": "air_conditioner", "name": "中央空调",
        "room": "客厅", "online": True,
        "commands": [
            {"name": "turn_on", "params": {}},
            {"name": "turn_off", "params": {}},
            {"name": "set_temperature", "params": {"temperature": {"type": "integer", "min": 16, "max": 30}}},
            {"name": "set_mode", "params": {"mode": {"type": "enum", "values": ["cool", "auto", "dry", "fan"]}}},
            {"name": "set_fan_speed", "params": {"fan_speed": {"type": "enum", "values": ["low", "medium", "high"]}}},
        ],
    },
    {
        "id": "light-living-001", "type": "light", "name": "客厅主灯",
        "room": "客厅", "online": True,
        "commands": [
            {"name": "turn_on", "params": {}},
            {"name": "turn_off", "params": {}},
            {"name": "set_brightness", "params": {"brightness": {"type": "integer", "min": 0, "max": 100}}},
            {"name": "set_color_temperature", "params": {"color_temperature": {"type": "integer", "min": 2700, "max": 6500}}},
        ],
    },
    {
        "id": "light-bedroom-001", "type": "light", "name": "卧室氛围灯",
        "room": "主卧", "online": True,
        "commands": [
            {"name": "turn_on", "params": {}},
            {"name": "turn_off", "params": {}},
            {"name": "set_brightness", "params": {"brightness": {"type": "integer", "min": 0, "max": 100}}},
        ],
    },
    {
        "id": "tv-living-001", "type": "tv", "name": "智能电视",
        "room": "客厅", "online": True,
        "commands": [
            {"name": "turn_on", "params": {}},
            {"name": "turn_off", "params": {}},
            {"name": "set_volume", "params": {"volume": {"type": "integer", "min": 0, "max": 100}}},
            {"name": "set_source", "params": {"source": {"type": "string"}}},
            {"name": "set_channel", "params": {"channel": {"type": "integer", "min": 1, "max": 999}}},
        ],
    },
]

TEST_SCENES = [
    {"id": "home", "name": "回家"},
    {"id": "movie", "name": "观影"},
    {"id": "sleep", "name": "睡眠"},
    {"id": "away", "name": "离家"},
]


def _post(path: str, body: dict | bytes | None = None, content_type: str = "application/json") -> dict:
    """发送 HTTP POST 请求。"""
    url = f"{BASE_URL}{path}"
    data = None
    if body is not None:
        if isinstance(body, bytes):
            data = body
        else:
            data = json.dumps(body).encode("utf-8")

    headers = {}
    if content_type and data is not None and not isinstance(body, bytes):
        headers["Content-Type"] = content_type

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return {"status": e.code, "body": body}


def _get(path: str) -> dict:
    """发送 HTTP GET 请求。"""
    url = f"{BASE_URL}{path}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return {"status": resp.status, "body": json.loads(resp.read())}


def _make_test_audio(size: int = 32000) -> bytes:
    """生成模拟 WAV 音频数据。"""
    return bytes([(i % 256) or 1 for i in range(size)])


def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_ok(msg: str):
    print(f"  ✅ {msg}")


def print_fail(msg: str):
    print(f"  ❌ {msg}")


def print_info(msg: str):
    print(f"  ℹ️  {msg}")


# ── 测试步骤 ────────────────────────────────────────────────────────────

def test_health():
    """§11.2 内部健康检查"""
    print_header("1. 健康检查 — GET /internal/health")
    resp = _get("/internal/health")
    body = resp["body"]

    assert resp["status"] == 200, f"状态码应为 200，实际 {resp['status']}"
    assert body["status"] == "ok"
    assert "models" in body
    print_ok(f"服务状态: {body}")
    return True


def test_asr():
    """§8.1 ASR 转写"""
    print_header("2. ASR 转写 — POST /internal/v1/asr/transcriptions")
    audio = _make_test_audio(64000)  # 约 2 秒

    # 用 multipart 方式发送
    boundary = "----TestBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="audio"; filename="test.wav"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode() + audio + f"\r\n--{boundary}--\r\n".encode()

    url = f"{BASE_URL}/internal/v1/asr/transcriptions"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print_fail(f"HTTP {e.code}: {e.read().decode()[:200]}")
        return False

    assert "text" in data, f"缺少 text 字段: {data}"
    assert "language" in data
    assert "confidence" in data
    print_ok(f"转写结果: \"{data['text']}\" (置信度: {data['confidence']}, 引擎: {data.get('engine', 'unknown')})")
    return True


def test_nlu(case_name: str, text: str, expected_device: str | None, expected_command: str | None):
    """§8.2 NLU 意图解析"""
    print_header(f"3. NLU 意图解析 — \"{text}\"")
    resp = _post("/internal/v1/nlu/interpret", {
        "text": text,
        "devices": TEST_DEVICES,
        "scenes": TEST_SCENES,
    })
    body = resp["body"]

    assert resp["status"] == 200, f"状态码应为 200，实际 {resp['status']}"
    assert "understood" in body
    assert "reply" in body
    assert "actions" in body

    understood = body["understood"]
    reply = body["reply"]
    actions = body["actions"]

    print_info(f"理解: {'是' if understood else '否'} | 回复: \"{reply}\"")
    if actions:
        for a in actions:
            if a["kind"] == "device_command":
                print_info(f"  → 设备: {a['device_id']}, 命令: {a['command']}, 参数: {a['params']}")
            elif a["kind"] == "scene":
                print_info(f"  → 场景: {a['scene_id']}")

    # 验证预期
    if expected_device and expected_command:
        if not understood:
            print_fail(f"预期 understood=true，实际=false")
            return False
        found = any(
            a.get("device_id") == expected_device and a.get("command") == expected_command
            for a in actions
        )
        if not found:
            print_fail(f"预期动作包含 device={expected_device}, command={expected_command}")
            return False
        print_ok("动作匹配预期")
    elif expected_device is None and expected_command is None and "那个" in text:
        # 模糊指令应返回 understood=false
        if understood:
            print_fail(f"预期 understood=false，实际=true")
            return False
        print_ok("模糊指令正确拒绝")

    return True


def test_tts():
    """§8.3 TTS 语音合成"""
    print_header("4. TTS 语音合成 — POST /internal/v1/tts/speech")
    resp = _post("/internal/v1/tts/speech", {
        "text": "你好，欢迎使用智能家居系统。",
        "voice": "default",
        "format": "wav",
    })
    body = resp["body"]

    assert resp["status"] == 200, f"状态码应为 200，实际 {resp['status']}"
    assert body["status"] == "success"
    assert "audio_url" in body
    print_ok(f"音频 URL: {body['audio_url']}")
    print_info(f"引擎: {'DashScope 云端' if body.get('request_id') else 'pyttsx3 本地降级'}")
    return True


# ── 主流程 ───────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  AI Service 端到端流水线测试")
    print(f"  服务地址: {BASE_URL}")
    print("=" * 60)

    # 先检查服务是否可达
    try:
        _get("/ai/health")
    except Exception as e:
        print(f"\n❌ 无法连接到 AI Service ({BASE_URL})")
        print(f"   请先启动服务: cd smart-home-system/ai-service && uvicorn src.main:app --port 8001")
        print(f"   错误: {e}")
        sys.exit(1)

    results = []

    # 1. 健康检查
    results.append(("健康检查", test_health()))

    # 2. ASR
    results.append(("ASR 转写", test_asr()))

    # 3. NLU 意图解析（多组测试）
    for name, text, exp_dev, exp_cmd in TEST_CASES:
        results.append((f"NLU: {name}", test_nlu(name, text, exp_dev, exp_cmd)))

    # 4. TTS
    results.append(("TTS 合成", test_tts()))

    # ── 汇总 ─────────────────────────────────────────────────────────
    print_header("测试汇总")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
    print(f"\n  通过: {passed}/{total}")
    if passed == total:
        print("  🎉 全部测试通过！")
    else:
        print("  ⚠️  部分测试失败，请检查上方详情")
        sys.exit(1)


if __name__ == "__main__":
    main()
