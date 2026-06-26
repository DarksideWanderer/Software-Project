import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import home_orchestrator


async def _client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def disable_tts_by_default(monkeypatch):
    async def fake_synthesize_reply_speech(reply):
        return None

    monkeypatch.setattr(home_orchestrator, "synthesize_reply_speech", fake_synthesize_reply_speech)


@pytest.mark.asyncio
async def test_root_explains_backend_entrypoints():
    async with await _client() as client:
        resp = await client.get("/")

    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "backend-core"
    assert body["endpoints"]["dashboard"] == "/api/v1/dashboard"


@pytest.mark.asyncio
async def test_file_origin_cors_preflight_for_local_demo():
    async with await _client() as client:
        resp = await client.options(
            "/api/v1/assistant/messages",
            headers={
                "Origin": "null",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "null"


@pytest.mark.asyncio
async def test_dashboard_exposes_three_demo_devices():
    async with await _client() as client:
        resp = await client.get("/api/v1/dashboard")

    assert resp.status_code == 200
    body = resp.json()
    assert [device["id"] for device in body["devices"]] == ["ac-001", "light-001", "tv-001"]
    assert body["summary"]["total"] == 3
    assert {scene["id"] for scene in body["scenes"]} == {"home", "movie", "away"}


@pytest.mark.asyncio
async def test_device_command_uses_product_model_when_simulator_is_offline():
    async with await _client() as client:
        resp = await client.post(
            "/api/v1/devices/ac-001/commands",
            json={"command": "set_temperature", "params": {"temperature": 99}},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["params"]["temperature"] == 30
    assert body["device"]["id"] == "ac-001"


@pytest.mark.asyncio
async def test_scene_execute_returns_device_results():
    async with await _client() as client:
        resp = await client.post("/api/v1/scenes/movie/execute")

    assert resp.status_code == 200
    body = resp.json()
    assert body["scene"]["id"] == "movie"
    assert len(body["results"]) == 6
    assert len(body["devices"]) == 3


@pytest.mark.asyncio
async def test_assistant_message_executes_nlu_actions(monkeypatch):
    async def fake_call_nlu(text, conversation=None):
        return {
            "understood": True,
            "reply": "好的，正在处理中央空调。",
            "actions": [
                {
                    "kind": "device_command",
                    "device_id": "ac-001",
                    "command": "set_temperature",
                    "params": {"temperature": 26},
                }
            ],
        }

    monkeypatch.setattr(home_orchestrator, "call_nlu", fake_call_nlu)

    async with await _client() as client:
        resp = await client.post("/api/v1/assistant/messages", json={"text": "把空调调到 26 度"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["understood"] is True
    assert body["actions"][0]["device_id"] == "ac-001"
    assert body["results"][0]["command"] == "set_temperature"


@pytest.mark.asyncio
async def test_assistant_message_accepts_message_alias(monkeypatch):
    async def fake_call_nlu(text, conversation=None):
        assert text == "打开客厅灯"
        return {
            "understood": True,
            "reply": "好的，客厅主灯已打开。",
            "actions": [
                {"kind": "device_command", "device_id": "light-001", "command": "turn_on", "params": {}}
            ],
        }

    monkeypatch.setattr(home_orchestrator, "call_nlu", fake_call_nlu)

    async with await _client() as client:
        resp = await client.post("/api/v1/assistant/messages", json={"message": "打开客厅灯"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "打开客厅灯"
    assert body["actions"][0]["device_id"] == "light-001"


@pytest.mark.asyncio
async def test_assistant_message_includes_tts_speech(monkeypatch):
    async def fake_call_nlu(text, conversation=None):
        return {
            "understood": True,
            "reply": "好的，客厅主灯已打开。",
            "actions": [],
        }

    async def fake_synthesize_reply_speech(reply):
        assert reply == "好的，客厅主灯已打开。"
        return {
            "url": "/api/v1/audio/tts/demo.wav",
            "content_type": "audio/wav",
            "expires_at": "2026-06-22T20:30:00+08:00",
        }

    monkeypatch.setattr(home_orchestrator, "call_nlu", fake_call_nlu)
    monkeypatch.setattr(home_orchestrator, "synthesize_reply_speech", fake_synthesize_reply_speech)

    async with await _client() as client:
        resp = await client.post("/api/v1/assistant/messages", json={"text": "打开客厅灯"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "好的，客厅主灯已打开。"
    assert body["speech"] == {
        "url": "/api/v1/audio/tts/demo.wav",
        "content_type": "audio/wav",
        "expires_at": "2026-06-22T20:30:00+08:00",
    }


@pytest.mark.asyncio
async def test_assistant_message_ignores_tts_failure(monkeypatch):
    async def fake_call_nlu(text, conversation=None):
        return {
            "understood": True,
            "reply": "好的，正在处理。",
            "actions": [],
        }

    async def fake_synthesize_reply_speech(reply):
        raise RuntimeError("tts down")

    monkeypatch.setattr(home_orchestrator, "call_nlu", fake_call_nlu)
    monkeypatch.setattr(home_orchestrator, "synthesize_reply_speech", fake_synthesize_reply_speech)

    async with await _client() as client:
        resp = await client.post("/api/v1/assistant/messages", json={"text": "打开客厅灯"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "好的，正在处理。"
    assert "speech" not in body


@pytest.mark.asyncio
async def test_assistant_voice_reuses_text_flow(monkeypatch):
    async def fake_transcribe_audio(audio, language="zh-CN"):
        return {"text": "打开客厅灯", "language": language, "confidence": 0.9}

    async def fake_call_nlu(text, conversation=None):
        return {
            "understood": True,
            "reply": "好的，正在处理客厅主灯。",
            "actions": [
                {"kind": "device_command", "device_id": "light-001", "command": "turn_on", "params": {}}
            ],
        }

    monkeypatch.setattr(home_orchestrator, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(home_orchestrator, "call_nlu", fake_call_nlu)

    async with await _client() as client:
        resp = await client.post(
            "/api/v1/assistant/voice",
            files={"audio": ("recording.wav", b"0" * 512, "audio/wav")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript"]["text"] == "打开客厅灯"
    assert body["actions"][0]["device_id"] == "light-001"


@pytest.mark.asyncio
async def test_assistant_voice_includes_tts_speech(monkeypatch):
    async def fake_transcribe_audio(audio, language="zh-CN"):
        return {"text": "打开客厅灯", "language": language, "confidence": 0.9}

    async def fake_call_nlu(text, conversation=None):
        return {
            "understood": True,
            "reply": "好的，正在处理客厅主灯。",
            "actions": [],
        }

    async def fake_synthesize_reply_speech(reply):
        return {"url": "/api/v1/audio/tts/voice.wav", "content_type": "audio/wav"}

    monkeypatch.setattr(home_orchestrator, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(home_orchestrator, "call_nlu", fake_call_nlu)
    monkeypatch.setattr(home_orchestrator, "synthesize_reply_speech", fake_synthesize_reply_speech)

    async with await _client() as client:
        resp = await client.post(
            "/api/v1/assistant/voice",
            files={"audio": ("recording.wav", b"0" * 512, "audio/wav")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript"]["text"] == "打开客厅灯"
    assert body["speech"]["url"] == "/api/v1/audio/tts/voice.wav"


def test_tts_relative_audio_url_uses_backend_proxy():
    speech = home_orchestrator._normalize_tts_speech(
        {
            "status": "success",
            "audio_url": "/internal/v1/tts/audio/local-file.wav",
            "content_type": "audio/wav",
            "expires_at": "2026-06-22T20:30:00+08:00",
        }
    )

    assert speech == {
        "url": "/api/v1/audio/tts/local-file.wav",
        "content_type": "audio/wav",
        "expires_at": "2026-06-22T20:30:00+08:00",
    }
