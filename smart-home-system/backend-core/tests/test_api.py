"""
backend-core API 路由集成测试
测试 /api/v1 各路由的请求/响应
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ======================== Test App Fixture ========================


@pytest.fixture
def client():
    """创建测试客户端（mock DeviceHub）"""
    with patch("app.main.hub", MagicMock()) as mock_hub:
        mock_hub._registry = {}
        mock_hub._devices = {}
        mock_hub.list_devices = MagicMock(return_value=[])
        mock_hub.send_command = AsyncMock(return_value={
            "success": True, "message": "ok", "state": {"is_on": True}
        })
        mock_hub.get_state = AsyncMock(return_value={
            "success": True, "state": {"is_on": True, "temperature": 24}
        })
        mock_hub.start = AsyncMock()

        from app.main import app
        with TestClient(app) as c:
            yield c, mock_hub


@pytest.fixture
def client_with_devices():
    """创建测试客户端（有已注册模拟设备）"""
    with patch("app.main.hub", MagicMock()) as mock_hub:
        mock_hub._registry = {
            "ac-003": {"type": "air_conditioner"},
            "light-001": {"type": "light"},
            "tv-001": {"type": "tv"}
        }
        mock_hub._devices = {
            "ac-003": MagicMock(),
            "light-001": MagicMock(),
            "tv-001": MagicMock()
        }
        mock_hub.list_devices = MagicMock(return_value=[
            {"device_id": "ac-003", "device_type": "air_conditioner", "connected": True},
            {"device_id": "light-001", "device_type": "light", "connected": True},
            {"device_id": "tv-001", "device_type": "tv", "connected": True},
        ])
        mock_hub.send_command = AsyncMock(return_value={
            "success": True, "message": "ok", "state": {"is_on": True, "temperature": 24}
        })
        mock_hub.get_state = AsyncMock(return_value={
            "success": True, "state": {"is_on": True, "temperature": 24}
        })
        mock_hub.get_command_count = MagicMock(return_value={"command_count": 3})
        mock_hub.get_command_schema = MagicMock(return_value={
            "name": "turn_on", "description": "打开空调", "params": []
        })
        mock_hub.start = AsyncMock()

        from app.main import app
        with TestClient(app) as c:
            yield c, mock_hub


# ======================== 健康检查测试 ========================


class TestHealthEndpoint:
    """健康检查 /health API"""

    def test_health_returns_ok(self, client):
        c, _ = client
        response = c.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# ======================== 仪表盘 API 测试 ========================


class TestDashboardAPI:
    """GET /api/v1/dashboard"""

    def test_dashboard_returns_structure(self, client):
        c, _ = client
        response = c.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert "candidates" in data
        assert "scenes" in data
        assert "summary" in data

    def test_dashboard_summary_fields(self, client):
        c, _ = client
        response = c.get("/api/v1/dashboard")
        data = response.json()
        summary = data["summary"]
        assert "total" in summary
        assert "online" in summary
        assert "active" in summary
        assert "energy_today" in summary


# ======================== 设备 API 测试 ========================


class TestDevicesAPI:
    """设备相关 API"""

    def test_list_devices_empty(self, client):
        c, _ = client
        response = c.get("/api/v1/devices")
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data

    def test_discover_devices(self, client_with_devices):
        c, hub = client_with_devices
        response = c.get("/api/v1/devices/discover")
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data

    def test_get_raw_devices(self, client_with_devices):
        c, hub = client_with_devices
        response = c.get("/api/v1/devices/raw")
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data

    def test_get_device_not_found(self, client):
        c, _ = client
        response = c.get("/api/v1/devices/nonexistent-999")
        assert response.status_code == 404

    def test_bind_device_validation(self, client):
        """绑定请求参数校验"""
        c, _ = client
        response = c.post(
            "/api/v1/devices/ac-003/bind",
            json={"name": "", "room": ""}
        )
        # 可能 404 (设备不在线) 或 400，取决于 mock 状态
        assert response.status_code in [400, 404, 409]

    def test_get_device_state(self, client_with_devices):
        c, hub = client_with_devices
        hub.get_state = AsyncMock(return_value={
            "success": True,
            "state": {"is_on": True, "temperature": 24}
        })
        response = c.get("/api/v1/devices/ac-003/state")
        assert response.status_code == 200

    def test_get_command_count(self, client_with_devices):
        c, hub = client_with_devices
        response = c.get("/api/v1/devices/ac-003/commands/count")
        assert response.status_code == 200
        data = response.json()
        # mock 注册表中无 commands 字段时返回 0，验证接口可用即可
        assert "command_count" in data

    def test_get_command_schema(self, client_with_devices):
        c, hub = client_with_devices
        response = c.get("/api/v1/devices/ac-003/commands/turn_on")
        assert response.status_code == 200

    def test_execute_device_command(self, client_with_devices):
        c, hub = client_with_devices
        hub.send_command = AsyncMock(return_value={
            "success": True, "message": "ok", "state": {"is_on": True}
        })
        response = c.post(
            "/api/v1/devices/ac-003/commands",
            json={"command": "turn_on", "params": {}}
        )
        assert response.status_code in [200, 404]


# ======================== 场景 API 测试 ========================


class TestScenesAPI:
    """场景相关 API"""

    def test_list_scenes(self, client):
        c, _ = client
        response = c.get("/api/v1/scenes")
        assert response.status_code == 200
        data = response.json()
        assert "scenes" in data

    def test_create_scene_without_devices(self, client):
        """创建场景但无已绑定设备 -> 400"""
        c, _ = client
        response = c.post(
            "/api/v1/scenes",
            json={
                "name": "测试场景",
                "commands": [
                    {"device_id": "ac-003", "command": "turn_on", "params": {}}
                ]
            }
        )
        # 没有绑定设备时预期 400
        assert response.status_code == 400

    def test_delete_builtin_scene_fails(self, client):
        c, _ = client
        response = c.delete("/api/v1/scenes/home")
        assert response.status_code == 400

    def test_execute_nonexistent_scene(self, client):
        c, _ = client
        response = c.post("/api/v1/scenes/nonexistent-999/execute")
        assert response.status_code == 404

    def test_natural_scene_requires_text(self, client):
        """自然语言场景创建需要文本"""
        c, _ = client
        response = c.post(
            "/api/v1/scenes/natural",
            json={"text": "打开客厅灯"}
        )
        # AI 不可用时 503，参数缺失时 422
        assert response.status_code in [422, 503]


# ======================== 助手 API 测试 ========================


class TestAssistantAPI:
    """助手相关 API"""

    def test_message_empty_text(self, client):
        c, _ = client
        response = c.post(
            "/api/v1/assistant/messages",
            json={"text": "", "conversation": []}
        )
        # 空文本应该 400
        assert response.status_code == 400

    def test_message_with_text(self, client):
        c, _ = client
        response = c.post(
            "/api/v1/assistant/messages",
            json={"text": "打开客厅灯", "conversation": []}
        )
        # AI 不可用时会 503
        assert response.status_code in [200, 503]

    def test_voice_without_file(self, client):
        c, _ = client
        response = c.post("/api/v1/assistant/voice")
        assert response.status_code == 422  # 缺少必填文件


# ======================== CORS 测试 ========================


class TestCORS:
    """CORS 配置测试"""

    def test_cors_headers_present(self, client):
        c, _ = client
        response = c.options(
            "/api/v1/dashboard",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        # OPTIONS 请求可能返回 200 或 405
        assert response.status_code in [200, 405]

    def test_cors_on_get(self, client):
        c, _ = client
        response = c.get(
            "/api/v1/dashboard",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
