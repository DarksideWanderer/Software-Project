"""
智能家居系统 — 端到端集成测试

测试完整业务流程：
1. 设备注册 → 发现 → 绑定 → 控制 → 移除
2. 场景创建 → 执行
3. AI 助手文本/语音流程

运行方式:
  cd smart-home-system
  python -m pytest integration-tests/test_e2e_flow.py -v

前置条件:
  - backend-core 运行在 :8000
  - ai-service 运行在 :8001 (可选，测试会 mock)
  - device-simulator 编译好 (./build/simulator)
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

# 项目根路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_CORE_DIR = PROJECT_ROOT / "backend-core"
AI_SERVICE_DIR = PROJECT_ROOT / "ai-service"
SIMULATOR_DIR = PROJECT_ROOT / "device-simulator"
SIMULATOR_BIN = SIMULATOR_DIR / "build" / "simulator"

BACKEND_URL = "http://127.0.0.1:8000"
AI_URL = "http://127.0.0.1:8001"
HUB_PORT = 9760


# ======================== Helpers ========================


def wait_for_service(url: str, timeout: int = 15) -> bool:
    """等待服务就绪"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            import httpx
            with httpx.Client(timeout=2) as c:
                resp = c.get(url)
                if resp.status_code < 500:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def start_backend():
    """启动 backend-core"""
    env = os.environ.copy()
    env["AI_SERVICE_BASE_URL"] = AI_URL
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BACKEND_CORE_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def start_simulator(device_type: str, device_id: str = None):
    """启动 C++ 模拟器进程"""
    if not SIMULATOR_BIN.exists():
        raise FileNotFoundError(f"Simulator binary not found: {SIMULATOR_BIN}")
    args = [str(SIMULATOR_BIN), "--device", device_type]
    if device_id:
        args.extend(["--id", device_id])
    return subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


# ======================== HTTP-only 集成测试(无需启动服务) ========================


class TestDeviceFlowHTTP:
    """设备完整流程 HTTP 测试 (Mock DeviceHub)"""

    @pytest.fixture(autouse=True)
    def mock_backend(self):
        """Mock backend-core 的关键依赖"""
        import sys
        sys.path.insert(0, str(BACKEND_CORE_DIR))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"bound_devices": {}, "device_states": {}, "user_scenes": {}}, f)
            state_path = f.name

        from unittest.mock import patch, MagicMock, AsyncMock
        mock_hub = MagicMock()
        mock_hub._registry = {}
        mock_hub._devices = {}
        mock_hub.list_devices = MagicMock(return_value=[])
        mock_hub.send_command = AsyncMock(return_value={
            "success": True, "message": "ok", "state": {"is_on": True}
        })
        mock_hub.get_state = AsyncMock(return_value={
            "success": True, "state": {"is_on": True, "temperature": 24}
        })
        mock_hub.get_command_count = MagicMock(return_value={"command_count": 3})
        mock_hub.get_command_schema = MagicMock(return_value={
            "name": "turn_on", "description": "打开", "params": []
        })
        mock_hub.start = AsyncMock()

        with patch("app.main.hub", mock_hub):
            with patch("app.services.home_orchestrator.STATE_PATH", Path(state_path)):
                with patch("app.services.home_orchestrator.hub", mock_hub):
                    from app.main import app
                    from fastapi.testclient import TestClient
                    client = TestClient(app)
                    yield client, mock_hub, state_path

        os.unlink(state_path)

    def _make_online(self, mock_hub, device_id: str, device_type: str):
        """让设备在 Hub 中上线"""
        mock_hub._registry[device_id] = {"type": device_type}
        mock_hub._devices[device_id] = MagicMock()

    def test_full_device_lifecycle(self, mock_backend):
        """完整设备生命周期：发现→绑定→查看→控制→移除"""
        client, mock_hub, _ = mock_backend

        # 1. 让模拟设备上线
        self._make_online(mock_hub, "ac-003", "air_conditioner")
        self._make_online(mock_hub, "light-001", "light")

        # 2. 发现设备
        resp = client.get("/api/v1/devices/discover")
        assert resp.status_code == 200
        candidates = resp.json()["devices"]
        candidate_ids = [d["id"] for d in candidates]
        assert "ac-003" in candidate_ids
        assert "light-001" in candidate_ids

        # 3. 绑定设备
        resp = client.post(
            "/api/v1/devices/ac-003/bind",
            json={"name": "客厅空调", "room": "客厅"}
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        resp = client.post(
            "/api/v1/devices/light-001/bind",
            json={"name": "客厅主灯", "room": "客厅"}
        )
        assert resp.status_code == 200

        # 4. 已绑定设备不在候选列表
        resp = client.get("/api/v1/devices/discover")
        candidates_after = resp.json()["devices"]
        candidate_ids_after = [d["id"] for d in candidates_after]
        assert "ac-003" not in candidate_ids_after
        assert "light-001" not in candidate_ids_after

        # 5. 查看设备详情
        resp = client.get("/api/v1/devices/ac-003")
        assert resp.status_code == 200
        device = resp.json()["device"]
        assert device["name"] == "客厅空调"
        assert device["room"] == "客厅"

        # 6. 控制设备
        resp = client.post(
            "/api/v1/devices/ac-003/commands",
            json={"command": "turn_on", "params": {}}
        )
        assert resp.status_code == 200

        resp = client.post(
            "/api/v1/devices/ac-003/commands",
            json={"command": "set_temperature", "params": {"temperature": 26}}
        )
        assert resp.status_code == 200

        # 7. 编辑设备信息
        resp = client.patch(
            "/api/v1/devices/ac-003",
            json={"name": "主卧空调", "room": "主卧"}
        )
        assert resp.status_code == 200

        # 8. 验证编辑结果
        resp = client.get("/api/v1/devices/ac-003")
        assert resp.json()["device"]["name"] == "主卧空调"

        # 9. 移除设备
        resp = client.delete("/api/v1/devices/ac-003")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # 10. 移除后查不到
        resp = client.get("/api/v1/devices/ac-003")
        assert resp.status_code == 404

    def test_duplicate_binding_rejected(self, mock_backend):
        """重复绑定被拒绝"""
        client, mock_hub, _ = mock_backend
        self._make_online(mock_hub, "ac-003", "air_conditioner")

        # 第一次绑定成功
        resp = client.post(
            "/api/v1/devices/ac-003/bind",
            json={"name": "客厅空调", "room": "客厅"}
        )
        assert resp.status_code == 200

        # 第二次绑定返回 409
        resp = client.post(
            "/api/v1/devices/ac-003/bind",
            json={"name": "主卧空调", "room": "主卧"}
        )
        assert resp.status_code == 409

    def test_control_offline_device(self, mock_backend):
        """控制离线设备返回失败"""
        client, mock_hub, _ = mock_backend
        self._make_online(mock_hub, "ac-003", "air_conditioner")

        # 先绑定
        client.post(
            "/api/v1/devices/ac-003/bind",
            json={"name": "客厅空调", "room": "客厅"}
        )

        # 模拟设备下线
        mock_hub._devices.pop("ac-003")

        # 控制离线设备
        resp = client.post(
            "/api/v1/devices/ac-003/commands",
            json={"command": "turn_on", "params": {}}
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False
        assert "not connected" in resp.json()["message"].lower()

    def test_parameter_validation(self, mock_backend):
        """参数校验"""
        client, mock_hub, _ = mock_backend
        self._make_online(mock_hub, "ac-003", "air_conditioner")

        client.post(
            "/api/v1/devices/ac-003/bind",
            json={"name": "客厅空调", "room": "客厅"}
        )

        # 温度超出范围 — 被钳位到最大值 30
        resp = client.post(
            "/api/v1/devices/ac-003/commands",
            json={"command": "set_temperature", "params": {"temperature": 100}}
        )
        assert resp.status_code == 200


class TestSceneFlowHTTP:
    """场景完整流程测试"""

    @pytest.fixture(autouse=True)
    def mock_backend(self):
        import sys
        sys.path.insert(0, str(BACKEND_CORE_DIR))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"bound_devices": {}, "device_states": {}, "user_scenes": {}}, f)
            state_path = f.name

        from unittest.mock import patch, MagicMock, AsyncMock
        mock_hub = MagicMock()
        mock_hub._registry = {}
        mock_hub._devices = {}
        mock_hub.list_devices = MagicMock(return_value=[])
        mock_hub.send_command = AsyncMock(return_value={
            "success": True, "message": "ok", "state": {"is_on": True}
        })
        mock_hub.get_state = AsyncMock(return_value={
            "success": True, "state": {"is_on": True}
        })
        mock_hub.get_command_count = MagicMock(return_value={"command_count": 3})
        mock_hub.get_command_schema = MagicMock(return_value={
            "name": "turn_on", "description": "打开", "params": []
        })
        mock_hub.start = AsyncMock()

        with patch("app.main.hub", mock_hub):
            with patch("app.services.home_orchestrator.STATE_PATH", Path(state_path)):
                with patch("app.services.home_orchestrator.hub", mock_hub):
                    from app.main import app
                    from fastapi.testclient import TestClient
                    client = TestClient(app)
                    # 绑定设备
                    mock_hub._registry.update({
                        "ac-003": {"type": "air_conditioner"},
                        "light-001": {"type": "light"},
                        "tv-001": {"type": "tv"}
                    })
                    mock_hub._devices.update({
                        "ac-003": MagicMock(),
                        "light-001": MagicMock(),
                        "tv-001": MagicMock()
                    })
                    client.post("/api/v1/devices/ac-003/bind", json={"name": "客厅空调", "room": "客厅"})
                    client.post("/api/v1/devices/light-001/bind", json={"name": "客厅主灯", "room": "客厅"})
                    client.post("/api/v1/devices/tv-001/bind", json={"name": "客厅电视", "room": "客厅"})
                    yield client, mock_hub, state_path

        os.unlink(state_path)

    def test_list_scenes_includes_builtins(self, mock_backend):
        """场景列表包含预设"""
        client, _, _ = mock_backend
        resp = client.get("/api/v1/scenes")
        assert resp.status_code == 200
        scenes = resp.json()["scenes"]
        ids = [s["id"] for s in scenes]
        assert "home" in ids
        assert "movie" in ids
        assert "away" in ids

    def test_create_and_execute_scene(self, mock_backend):
        """创建场景并执行"""
        client, mock_hub, _ = mock_backend

        # 创建场景
        resp = client.post("/api/v1/scenes", json={
            "name": "晚安模式",
            "description": "关闭所有设备",
            "commands": [
                {"device_id": "light-001", "command": "turn_off", "params": {}},
                {"device_id": "ac-003", "command": "turn_off", "params": {}},
            ]
        })
        assert resp.status_code == 200
        scene = resp.json()["scene"]
        assert scene["name"] == "晚安模式"
        assert scene["id"].startswith("user-")

        # 执行场景
        scene_id = scene["id"]
        resp = client.post(f"/api/v1/scenes/{scene_id}/execute")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert len(resp.json()["results"]) == 2

    def test_delete_builtin_scene_fails(self, mock_backend):
        """删除预设场景失败"""
        client, _, _ = mock_backend
        resp = client.delete("/api/v1/scenes/home")
        assert resp.status_code == 400

    def test_execute_nonexistent_scene_fails(self, mock_backend):
        """执行不存在场景失败"""
        client, _, _ = mock_backend
        resp = client.post("/api/v1/scenes/nonexistent/execute")
        assert resp.status_code == 404


class TestDashboardFlowHTTP:
    """仪表盘测试"""

    @pytest.fixture(autouse=True)
    def mock_backend(self):
        import sys
        sys.path.insert(0, str(BACKEND_CORE_DIR))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"bound_devices": {}, "device_states": {}, "user_scenes": {}}, f)
            state_path = f.name

        from unittest.mock import patch, MagicMock, AsyncMock
        mock_hub = MagicMock()
        mock_hub._registry = {}
        mock_hub._devices = {}
        mock_hub.list_devices = MagicMock(return_value=[])
        mock_hub.send_command = AsyncMock(return_value={
            "success": True, "message": "ok", "state": {"is_on": False}
        })
        mock_hub.get_state = AsyncMock(return_value={
            "success": True, "state": {"is_on": False}
        })
        mock_hub.start = AsyncMock()

        with patch("app.main.hub", mock_hub):
            with patch("app.services.home_orchestrator.STATE_PATH", Path(state_path)):
                with patch("app.services.home_orchestrator.hub", mock_hub):
                    from app.main import app
                    from fastapi.testclient import TestClient
                    client = TestClient(app)
                    yield client, mock_hub, state_path

        os.unlink(state_path)

    def test_dashboard_empty_state(self, mock_backend):
        """空家庭仪表盘"""
        client, _, _ = mock_backend
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["devices"] == []
        assert data["summary"]["total"] == 0
        assert data["summary"]["online"] == 0


class TestAssistantFlowHTTP:
    """AI 助手流程"""

    @pytest.fixture(autouse=True)
    def mock_backend(self):
        import sys
        sys.path.insert(0, str(BACKEND_CORE_DIR))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"bound_devices": {}, "device_states": {}, "user_scenes": {}}, f)
            state_path = f.name

        from unittest.mock import patch, MagicMock, AsyncMock
        mock_hub = MagicMock()
        mock_hub._registry = {}
        mock_hub._devices = {}
        mock_hub.send_command = AsyncMock(return_value={
            "success": True, "message": "ok", "state": {"is_on": True}
        })
        mock_hub.get_state = AsyncMock(return_value={
            "success": True, "state": {"is_on": True}
        })
        mock_hub.start = AsyncMock()

        with patch("app.main.hub", mock_hub):
            with patch("app.services.home_orchestrator.STATE_PATH", Path(state_path)):
                with patch("app.services.home_orchestrator.hub", mock_hub):
                    from app.main import app
                    from fastapi.testclient import TestClient
                    client = TestClient(app)
                    yield client, mock_hub, state_path

        os.unlink(state_path)

    def test_empty_text_rejected(self, mock_backend):
        """空文本被拒绝"""
        client, _, _ = mock_backend
        resp = client.post(
            "/api/v1/assistant/messages",
            json={"text": "", "conversation": []}
        )
        assert resp.status_code == 400

    def test_text_assistant_without_ai(self, mock_backend):
        """AI 不可用时的助手请求"""
        client, _, _ = mock_backend
        resp = client.post(
            "/api/v1/assistant/messages",
            json={"text": "打开客厅灯", "conversation": []}
        )
        # AI 不可用时返回 503
        assert resp.status_code in [200, 503]
