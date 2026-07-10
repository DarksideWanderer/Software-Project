"""
backend-core HomeOrchestrator 单元测试
测试 services/home_orchestrator.py 核心业务逻辑

运行方式:
  cd smart-home-system/backend-core
  python -m pytest tests/test_orchestrator.py -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 确保 backend-core 在 Python path 中
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ======================== Fixtures ========================


@pytest.fixture
def temp_state_file():
    """创建临时状态文件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "bound_devices": {},
            "device_states": {},
            "user_scenes": {}
        }, f)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def mock_hub():
    """模拟 DeviceHub"""
    hub = MagicMock()
    hub._registry = {}
    hub._devices = {}
    hub.send_command = AsyncMock(return_value={
        "success": True,
        "message": "ok",
        "state": {"is_on": True, "temperature": 24}
    })
    hub.get_state = AsyncMock(return_value={
        "success": True,
        "state": {"is_on": True, "temperature": 24}
    })
    return hub


@pytest.fixture
def populated_state_file():
    """含已绑定设备的状态文件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "bound_devices": {
                "ac-003": {
                    "id": "ac-003",
                    "type": "air_conditioner",
                    "name": "客厅空调",
                    "room": "客厅",
                    "original_name": "ac-003"
                },
                "light-001": {
                    "id": "light-001",
                    "type": "light",
                    "name": "客厅主灯",
                    "room": "客厅",
                    "original_name": "light-001"
                }
            },
            "device_states": {
                "ac-003": {"is_on": True, "temperature": 24},
                "light-001": {"is_on": False, "brightness": 70}
            },
            "user_scenes": {}
        }, f)
        path = f.name
    yield path
    os.unlink(path)


# ======================== 状态读写测试 ========================


class TestStatePersistence:
    """状态文件读写测试"""

    def test_load_empty_state_when_file_missing(self):
        """文件不存在时返回默认空状态"""
        from app.services.home_orchestrator import _load_state, _default_state
        with patch("app.services.home_orchestrator.STATE_PATH", Path("/nonexistent/path.json")):
            state = _load_state()
            assert state == _default_state()

    def test_save_and_load_state(self, temp_state_file):
        """写入状态后能正确读取"""
        from app.services.home_orchestrator import _load_state, _save_state
        with patch("app.services.home_orchestrator.STATE_PATH", Path(temp_state_file)):
            state = _load_state()
            state["bound_devices"]["test-001"] = {
                "id": "test-001", "type": "light", "name": "Test"
            }
            _save_state(state)
            loaded = _load_state()
            assert "test-001" in loaded["bound_devices"]

    def test_default_state_structure(self):
        """默认状态包含必要字段"""
        from app.services.home_orchestrator import _default_state
        state = _default_state()
        assert "bound_devices" in state
        assert "device_states" in state
        assert "user_scenes" in state
        assert state["bound_devices"] == {}
        assert state["user_scenes"] == {}


# ======================== 设备发现测试 ========================


class TestDeviceDiscovery:
    """设备发现功能测试"""

    def test_discover_returns_empty_when_no_registry(self, temp_state_file):
        """无注册设备时返回空列表"""
        from app.services.home_orchestrator import discover_devices
        with patch("app.services.home_orchestrator.STATE_PATH", Path(temp_state_file)):
            with patch("app.services.home_orchestrator.hub._registry", {}):
                result = discover_devices()
                assert result == []

    def test_discover_filters_bound_devices(self, populated_state_file, mock_hub):
        """已绑定设备不出现在候选列表"""
        from app.services.home_orchestrator import discover_devices
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
        with patch("app.services.home_orchestrator.STATE_PATH", Path(populated_state_file)):
            with patch("app.services.home_orchestrator.hub", mock_hub):
                result = discover_devices()
                # ac-003 和 light-001 已绑定，只有 tv-001 在候选列表中
                candidate_ids = [d["id"] for d in result]
                assert "ac-003" not in candidate_ids
                assert "light-001" not in candidate_ids
                assert "tv-001" in candidate_ids

    def test_discover_device_has_required_fields(self):
        """候选设备包含所有必要字段"""
        from app.services.home_orchestrator import discover_devices
        with patch("app.services.home_orchestrator.hub._registry", {
            "purifier-001": {"type": "air_purifier"}
        }):
            with patch("app.services.home_orchestrator.hub._devices", {
                "purifier-001": MagicMock()
            }):
                with patch("app.services.home_orchestrator._load_state", return_value={
                    "bound_devices": {}, "device_states": {}, "user_scenes": {}
                }):
                    result = discover_devices()
                    assert len(result) == 1
                    d = result[0]
                    for field in ["id", "type", "type_code", "type_label", "display", "online", "bound"]:
                        assert field in d, f"Missing field: {field}"


# ======================== 设备绑定测试 ========================


class TestDeviceBinding:
    """设备绑定功能测试"""

    def test_bind_device_success(self, temp_state_file, mock_hub):
        """绑定在线设备成功"""
        from app.services.home_orchestrator import bind_device
        mock_hub._registry = {"ac-003": {"type": "air_conditioner"}}
        mock_hub._devices = {"ac-003": MagicMock()}
        with patch("app.services.home_orchestrator.STATE_PATH", Path(temp_state_file)):
            with patch("app.services.home_orchestrator.hub", mock_hub):
                result = bind_device("ac-003", name="客厅空调", room="客厅")
                assert result["success"] is True
                assert result["device_id"] == "ac-003"

    def test_bind_duplicate_device_raises_409(self, populated_state_file, mock_hub):
        """重复绑定返回 409"""
        from app.services.home_orchestrator import bind_device
        from fastapi import HTTPException
        mock_hub._registry = {"ac-003": {"type": "air_conditioner"}}
        mock_hub._devices = {"ac-003": MagicMock()}
        with patch("app.services.home_orchestrator.STATE_PATH", Path(populated_state_file)):
            with patch("app.services.home_orchestrator.hub", mock_hub):
                with pytest.raises(HTTPException) as exc_info:
                    bind_device("ac-003")
                assert exc_info.value.status_code == 409

    def test_bind_offline_device_raises_404(self, temp_state_file, mock_hub):
        """绑定不在线设备返回 404"""
        from app.services.home_orchestrator import bind_device
        from fastapi import HTTPException
        mock_hub._registry = {"ac-003": {"type": "air_conditioner"}}
        mock_hub._devices = {}  # 不在线
        with patch("app.services.home_orchestrator.STATE_PATH", Path(temp_state_file)):
            with patch("app.services.home_orchestrator.hub", mock_hub):
                with pytest.raises(HTTPException) as exc_info:
                    bind_device("ac-003")
                assert exc_info.value.status_code == 404

    def test_bind_unknown_device_raises_404(self, temp_state_file):
        """绑定未知设备返回 404"""
        from app.services.home_orchestrator import bind_device
        from fastapi import HTTPException
        with patch("app.services.home_orchestrator.STATE_PATH", Path(temp_state_file)):
            with patch("app.services.home_orchestrator.hub._registry", {}):
                with pytest.raises(HTTPException) as exc_info:
                    bind_device("nonexistent-999")
                assert exc_info.value.status_code == 404


# ======================== 设备编辑与移除测试 ========================


class TestDeviceUpdate:
    """设备编辑测试"""

    def test_update_device_name(self, populated_state_file):
        """更新设备名称"""
        from app.services.home_orchestrator import update_bound_device
        with patch("app.services.home_orchestrator.STATE_PATH", Path(populated_state_file)):
            result = update_bound_device("ac-003", name="主卧空调")
            assert result["success"] is True

    def test_update_device_room(self, populated_state_file):
        """更新设备房间"""
        from app.services.home_orchestrator import update_bound_device
        with patch("app.services.home_orchestrator.STATE_PATH", Path(populated_state_file)):
            result = update_bound_device("light-001", room="卧室")
            assert result["success"] is True

    def test_update_unbound_device_raises_404(self, temp_state_file):
        """编辑未绑定设备返回 404"""
        from app.services.home_orchestrator import update_bound_device
        from fastapi import HTTPException
        with patch("app.services.home_orchestrator.STATE_PATH", Path(temp_state_file)):
            with pytest.raises(HTTPException) as exc_info:
                update_bound_device("nonexistent-999", name="test")
            assert exc_info.value.status_code == 404


class TestDeviceRemoval:
    """设备移除测试"""

    @pytest.mark.asyncio
    async def test_remove_device_success(self, populated_state_file):
        """移除已绑定设备成功"""
        from app.services.home_orchestrator import remove_device
        with patch("app.services.home_orchestrator.STATE_PATH", Path(populated_state_file)):
            result = await remove_device("ac-003")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_remove_unbound_device_raises_404(self, temp_state_file):
        """移除未绑定设备返回 404"""
        from app.services.home_orchestrator import remove_device
        from fastapi import HTTPException
        with patch("app.services.home_orchestrator.STATE_PATH", Path(temp_state_file)):
            with pytest.raises(HTTPException) as exc_info:
                await remove_device("nonexistent-999")
            assert exc_info.value.status_code == 404


# ======================== 设备类型元数据测试 ========================


class TestDeviceTypeMeta:
    """设备类型元数据测试"""

    def test_all_device_types_have_required_fields(self):
        """所有设备类型包含必要字段"""
        from app.services.home_orchestrator import DEVICE_TYPE_META
        required = ["label", "icon", "color", "soft", "glow", "energy", "defaults", "commands"]
        for device_type, meta in DEVICE_TYPE_META.items():
            for field in required:
                assert field in meta, f"{device_type} missing {field}"

    def test_air_conditioner_commands(self):
        """空调命令定义正确"""
        from app.services.home_orchestrator import DEVICE_TYPE_META
        ac = DEVICE_TYPE_META["air_conditioner"]
        assert "turn_on" in ac["commands"]
        assert "turn_off" in ac["commands"]
        assert "set_temperature" in ac["commands"]
        temp_cmd = ac["commands"]["set_temperature"]
        assert temp_cmd["params"]["temperature"]["min"] == 16
        assert temp_cmd["params"]["temperature"]["max"] == 30

    def test_light_commands(self):
        """灯光命令定义正确"""
        from app.services.home_orchestrator import DEVICE_TYPE_META
        light = DEVICE_TYPE_META["light"]
        assert "set_brightness" in light["commands"]
        assert "set_color" in light["commands"]
        color_param = light["commands"]["set_color"]["params"]["color"]
        assert "warm" in color_param["values"]
        assert "cool" in color_param["values"]

    def test_device_count_is_10(self):
        """支持 10 种设备类型"""
        from app.services.home_orchestrator import DEVICE_TYPE_META
        assert len(DEVICE_TYPE_META) == 10


# ======================== 参数校验测试 ========================


class TestParamCoercion:
    """参数校验与钳位测试 — 使用 DISCOVERABLE_DEVICES 中的已知 ID"""

    def test_coerce_integer_param_in_range(self):
        """整数参数在范围内保持不变"""
        from app.services.home_orchestrator import _coerce_params
        result = _coerce_params("ac-001", "set_temperature", {"temperature": 24})
        assert result["temperature"] == 24

    def test_coerce_integer_param_clamped_max(self):
        """整数参数超出最大值被钳位"""
        from app.services.home_orchestrator import _coerce_params
        result = _coerce_params("ac-001", "set_temperature", {"temperature": 100})
        assert result["temperature"] == 30

    def test_coerce_integer_param_clamped_min(self):
        """整数参数低于最小值被钳位"""
        from app.services.home_orchestrator import _coerce_params
        result = _coerce_params("ac-001", "set_temperature", {"temperature": -10})
        assert result["temperature"] == 16

    def test_coerce_string_param_valid(self):
        """字符串参数合法值通过"""
        from app.services.home_orchestrator import _coerce_params
        result = _coerce_params("light-001", "set_color", {"color": "warm"})
        assert result["color"] == "warm"

    def test_coerce_string_param_invalid_raises(self):
        """字符串参数非法值抛出异常"""
        from app.services.home_orchestrator import _coerce_params
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _coerce_params("light-001", "set_color", {"color": "purple"})

    def test_coerce_missing_required_param_raises(self):
        """缺少必填参数抛出异常"""
        from app.services.home_orchestrator import _coerce_params
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _coerce_params("ac-001", "set_temperature", {})

    def test_coerce_unknown_command_raises(self):
        """未知命令抛出异常"""
        from app.services.home_orchestrator import _coerce_params
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _coerce_params("ac-001", "fly_away", {})


# ======================== 场景管理测试 ========================


class TestSceneManagement:
    """场景管理功能测试"""

    def test_list_scenes_includes_builtin(self, temp_state_file):
        """场景列表包含预设场景"""
        from app.services.home_orchestrator import list_scenes
        with patch("app.services.home_orchestrator.STATE_PATH", Path(temp_state_file)):
            scenes = list_scenes()
            scene_ids = [s["id"] for s in scenes]
            assert "home" in scene_ids
            assert "movie" in scene_ids
            assert "away" in scene_ids

    def test_builtin_scenes_have_required_fields(self, temp_state_file):
        """预设场景包含必要字段"""
        from app.services.home_orchestrator import list_scenes
        with patch("app.services.home_orchestrator.STATE_PATH", Path(temp_state_file)):
            scenes = list_scenes()
            for scene in scenes:
                assert "id" in scene
                assert "name" in scene
                assert "commands" in scene
                assert "builtin" in scene

    def test_create_scene_success(self, populated_state_file):
        """创建场景成功"""
        from app.services.home_orchestrator import create_scene
        with patch("app.services.home_orchestrator.STATE_PATH", Path(populated_state_file)):
            scene = create_scene(
                name="测试场景",
                description="测试用",
                commands=[
                    {"device_id": "ac-003", "command": "turn_on", "params": {}}
                ]
            )
            assert scene["name"] == "测试场景"
            assert scene["id"].startswith("user-")
            assert scene["builtin"] is False

    def test_create_scene_with_unbound_device_raises(self, temp_state_file):
        """用未绑定设备创建场景抛出异常"""
        from app.services.home_orchestrator import create_scene
        from fastapi import HTTPException
        with patch("app.services.home_orchestrator.STATE_PATH", Path(temp_state_file)):
            with pytest.raises(HTTPException) as exc_info:
                create_scene(
                    name="无效场景",
                    commands=[
                        {"device_id": "ac-003", "command": "turn_on", "params": {}}
                    ]
                )
            assert exc_info.value.status_code == 400

    def test_delete_builtin_scene_raises(self, temp_state_file):
        """删除预设场景返回 400"""
        from app.services.home_orchestrator import delete_scene
        from fastapi import HTTPException
        with patch("app.services.home_orchestrator.STATE_PATH", Path(temp_state_file)):
            with pytest.raises(HTTPException) as exc_info:
                delete_scene("home")
            assert exc_info.value.status_code == 400

    def test_delete_user_scene_success(self, populated_state_file):
        """删除用户场景成功"""
        from app.services.home_orchestrator import delete_scene, create_scene
        with patch("app.services.home_orchestrator.STATE_PATH", Path(populated_state_file)):
            scene = create_scene(
                name="待删除",
                commands=[{"device_id": "ac-003", "command": "turn_on", "params": {}}]
            )
            result = delete_scene(scene["id"])
            assert result["success"] is True


# ======================== 命令优先级测试 ========================


class TestCommandPlanning:
    """动作规划测试"""

    def test_turn_on_before_params_before_turn_off(self):
        """开机 > 参数设置 > 关机排序"""
        from app.services.home_orchestrator import plan_actions
        actions = [
            {"kind": "device_command", "device_id": "ac-003", "command": "turn_off"},
            {"kind": "device_command", "device_id": "ac-003", "command": "set_temperature", "params": {"temperature": 26}},
            {"kind": "device_command", "device_id": "ac-003", "command": "turn_on"},
        ]
        planned = plan_actions(actions)
        commands = [a["command"] for a in planned]
        assert commands == ["turn_on", "set_temperature", "turn_off"]

    def test_scene_action_preserves_order(self):
        """场景 action 保持原始位置"""
        from app.services.home_orchestrator import plan_actions
        actions = [
            {"kind": "device_command", "device_id": "ac-003", "command": "turn_on"},
            {"kind": "scene", "scene_id": "movie"},
            {"kind": "device_command", "device_id": "light-001", "command": "turn_on"},
        ]
        planned = plan_actions(actions)
        assert planned[1]["kind"] == "scene"


# ======================== 类型推断测试 ========================


class TestTypeInference:
    """设备类型推断测试"""

    def test_type_from_id_ac(self):
        from app.services.home_orchestrator import _type_from_device_id
        assert _type_from_device_id("ac-003") == "air_conditioner"

    def test_type_from_id_light(self):
        from app.services.home_orchestrator import _type_from_device_id
        assert _type_from_device_id("light-001") == "light"

    def test_type_from_id_tv(self):
        from app.services.home_orchestrator import _type_from_device_id
        assert _type_from_device_id("tv-001") == "tv"

    def test_type_from_id_fridge(self):
        from app.services.home_orchestrator import _type_from_device_id
        assert _type_from_device_id("fridge-001") == "fridge"

    def test_type_from_id_washer(self):
        from app.services.home_orchestrator import _type_from_device_id
        assert _type_from_device_id("washer-001") == "washer"

    def test_type_from_id_heater(self):
        from app.services.home_orchestrator import _type_from_device_id
        assert _type_from_device_id("heater-001") == "water_heater"

    def test_type_from_id_purifier(self):
        from app.services.home_orchestrator import _type_from_device_id
        assert _type_from_device_id("purifier-001") == "air_purifier"

    def test_type_from_id_curtain(self):
        from app.services.home_orchestrator import _type_from_device_id
        assert _type_from_device_id("curtain-001") == "curtain"

    def test_type_from_id_socket(self):
        from app.services.home_orchestrator import _type_from_device_id
        assert _type_from_device_id("socket-001") == "socket"

    def test_type_from_id_robot(self):
        from app.services.home_orchestrator import _type_from_device_id
        assert _type_from_device_id("robot-001") == "robot_vacuum"

    def test_type_from_unknown_id(self):
        from app.services.home_orchestrator import _type_from_device_id
        assert _type_from_device_id("unknown-xyz") is None
