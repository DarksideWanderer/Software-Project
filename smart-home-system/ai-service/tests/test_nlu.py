"""NLU mock 模块测试。"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _devices():
    return [
        {
            "id": "light-living-001",
            "type": "light",
            "name": "客厅主灯",
            "room": "客厅",
            "online": True,
            "commands": [
                {"name": "turn_on", "params": {}},
                {"name": "turn_off", "params": {}},
                {
                    "name": "set_brightness",
                    "params": {"brightness": {"type": "integer", "min": 0, "max": 100}},
                },
            ],
        },
        {
            "id": "ac-living-001",
            "type": "air_conditioner",
            "name": "客厅空调",
            "room": "客厅",
            "online": True,
            "commands": [
                {"name": "turn_on", "params": {}},
                {"name": "turn_off", "params": {}},
                {
                    "name": "set_temperature",
                    "params": {"temperature": {"type": "integer", "min": 16, "max": 30}},
                },
            ],
        },
        {
            "id": "curtain-bedroom-001",
            "type": "curtain",
            "name": "卧室窗帘",
            "room": "卧室",
            "online": True,
            "commands": [
                {"name": "open", "params": {}},
                {"name": "close", "params": {}},
                {
                    "name": "set_open_percent",
                    "params": {"percent": {"type": "integer", "min": 0, "max": 100}},
                },
            ],
        },
    ]


def _scenes():
    return [{"id": "movie", "name": "观影"}, {"id": "sleep", "name": "睡眠"}]


@pytest.mark.asyncio
async def test_nlu_health(client: AsyncClient):
    resp = await client.get("/ai/nlu/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "module": "nlu"}


@pytest.mark.asyncio
async def test_internal_interpret_turn_on_light(client: AsyncClient):
    resp = await client.post(
        "/internal/v1/nlu/interpret",
        json={"text": "打开客厅灯", "devices": _devices(), "scenes": _scenes()},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["understood"] is True
    assert body["actions"] == [
        {
            "kind": "device_command",
            "device_id": "light-living-001",
            "command": "turn_on",
            "params": {},
        }
    ]


@pytest.mark.asyncio
async def test_interpret_set_air_conditioner_temperature(client: AsyncClient):
    resp = await client.post(
        "/internal/v1/nlu/interpret",
        json={"text": "把客厅空调调到22度", "devices": _devices(), "scenes": _scenes()},
    )

    body = resp.json()
    assert body["understood"] is True
    assert body["actions"][0]["device_id"] == "ac-living-001"
    assert body["actions"][0]["command"] == "set_temperature"
    assert body["actions"][0]["params"] == {"temperature": 22}


@pytest.mark.asyncio
async def test_interpret_multi_actions(client: AsyncClient):
    resp = await client.post(
        "/internal/v1/nlu/interpret",
        json={
            "text": "打开客厅灯并把空调调到22度",
            "devices": _devices(),
            "scenes": _scenes(),
        },
    )

    body = resp.json()
    assert body["understood"] is True
    assert body["actions"] == [
        {
            "kind": "device_command",
            "device_id": "light-living-001",
            "command": "turn_on",
            "params": {},
        },
        {
            "kind": "device_command",
            "device_id": "ac-living-001",
            "command": "set_temperature",
            "params": {"temperature": 22},
        },
    ]


@pytest.mark.asyncio
async def test_interpret_scene(client: AsyncClient):
    resp = await client.post(
        "/internal/v1/nlu/interpret",
        json={"text": "开启观影模式", "devices": _devices(), "scenes": _scenes()},
    )

    body = resp.json()
    assert body["understood"] is True
    assert body["actions"] == [{"kind": "scene", "scene_id": "movie"}]


@pytest.mark.asyncio
async def test_interpret_curtain_half_open(client: AsyncClient):
    resp = await client.post(
        "/internal/v1/nlu/interpret",
        json={"text": "卧室窗帘开一半", "devices": _devices(), "scenes": _scenes()},
    )

    body = resp.json()
    assert body["understood"] is True
    assert body["actions"][0]["device_id"] == "curtain-bedroom-001"
    assert body["actions"][0]["command"] == "set_open_percent"
    assert body["actions"][0]["params"] == {"percent": 50}


@pytest.mark.asyncio
async def test_interpret_missing_target_device(client: AsyncClient):
    resp = await client.post(
        "/internal/v1/nlu/interpret",
        json={"text": "打开厨房灯", "devices": _devices(), "scenes": _scenes()},
    )

    body = resp.json()
    assert body["understood"] is False
    assert body["actions"] == []


@pytest.mark.asyncio
async def test_interpret_does_not_use_unsupported_command(client: AsyncClient):
    devices = _devices()
    devices[0]["commands"] = [{"name": "turn_on", "params": {}}]
    resp = await client.post(
        "/internal/v1/nlu/interpret",
        json={"text": "把客厅灯亮度调到80", "devices": devices, "scenes": _scenes()},
    )

    body = resp.json()
    assert body["understood"] is False
    assert body["actions"] == []


@pytest.mark.asyncio
async def test_legacy_parse_compatibility(client: AsyncClient):
    resp = await client.post(
        "/ai/nlu/parse",
        json={"text": "打开客厅灯", "devices": _devices(), "scenes": _scenes()},
    )

    body = resp.json()
    assert body["understood"] is True
    assert body["actions"][0]["device_id"] == "light-living-001"
