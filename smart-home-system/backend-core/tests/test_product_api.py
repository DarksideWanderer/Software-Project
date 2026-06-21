import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import home_orchestrator


async def _client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


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
