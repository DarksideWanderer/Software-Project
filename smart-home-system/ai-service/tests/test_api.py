from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "device_control" in body["supported_intents"]


def test_nlu_endpoint():
    response = client.post("/ai/nlu", json={"text": "打开客厅灯"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "device_control"
    assert body["slots"]["device_type"] == "light"
    assert body["slots"]["location"] == "living_room"


def test_asr_mock_endpoint():
    response = client.post(
        "/ai/asr",
        json={
            "audio_base64": "",
            "format": "wav",
            "sample_rate": 16000,
            "mock_text": "打开客厅灯",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["text"] == "打开客厅灯"
    assert body["provider"] == "mock"
