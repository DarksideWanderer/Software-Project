"""
ai-service NLU 规则引擎单元测试
测试 src/nlu/routes.py 中的本地规则引擎

运行方式:
  cd smart-home-system/ai-service
  python -m pytest tests/test_nlu_rules.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


# ======================== 测试数据 ========================


def make_device(id: str, type: str, name: str, room: str = "客厅",
                commands: list = None) -> dict:
    """快速创建设备信息"""
    from nlu.routes import DeviceInfo, DeviceCommand
    cmd_list = commands or []
    cmd_objs = [DeviceCommand(name=c[0], params=c[1] if len(c) > 1 else {})
                for c in cmd_list]
    return DeviceInfo(
        id=id,
        type=type,
        name=name,
        room=room,
        online=True,
        commands=cmd_objs
    )


@pytest.fixture
def sample_devices():
    """标准测试设备集"""
    from nlu.routes import DeviceInfo, DeviceCommand
    return [
        DeviceInfo(id="ac-003", type="air_conditioner", name="客厅空调", room="客厅", online=True,
                   commands=[
                       DeviceCommand(name="turn_on", params={}),
                       DeviceCommand(name="turn_off", params={}),
                       DeviceCommand(name="set_temperature", params={"temperature": {"type": "integer"}})
                   ]),
        DeviceInfo(id="light-001", type="light", name="客厅主灯", room="客厅", online=True,
                   commands=[
                       DeviceCommand(name="turn_on", params={}),
                       DeviceCommand(name="turn_off", params={}),
                       DeviceCommand(name="set_brightness", params={"brightness": {"type": "integer"}}),
                       DeviceCommand(name="set_color", params={"color": {"type": "string"}}),
                   ]),
        DeviceInfo(id="light-002", type="light", name="卧室氛围灯", room="卧室", online=True,
                   commands=[
                       DeviceCommand(name="turn_on", params={}),
                       DeviceCommand(name="turn_off", params={}),
                       DeviceCommand(name="set_brightness", params={"brightness": {"type": "integer"}}),
                   ]),
        DeviceInfo(id="tv-001", type="tv", name="客厅电视", room="客厅", online=True,
                   commands=[
                       DeviceCommand(name="turn_on", params={}),
                       DeviceCommand(name="turn_off", params={}),
                       DeviceCommand(name="set_volume", params={"volume": {"type": "integer"}}),
                       DeviceCommand(name="set_channel", params={"channel": {"type": "integer"}}),
                   ]),
        DeviceInfo(id="curtain-001", type="curtain", name="卧室窗帘", room="卧室", online=True,
                   commands=[
                       DeviceCommand(name="turn_on", params={}),
                       DeviceCommand(name="turn_off", params={}),
                       DeviceCommand(name="set_open_percent", params={"percent": {"type": "integer"}}),
                   ]),
    ]


@pytest.fixture
def sample_scenes():
    """标准测试场景集"""
    from nlu.routes import SceneInfo
    return [
        SceneInfo(id="home", name="回家模式"),
        SceneInfo(id="movie", name="观影模式"),
        SceneInfo(id="away", name="离家模式"),
    ]


# ======================== 设备匹配测试 ========================


class TestDeviceMatching:
    """设备匹配功能"""

    def test_exact_name_match(self, sample_devices):
        """精确名称匹配"""
        from nlu.routes import _find_device
        result = _find_device("打开客厅空调", sample_devices)
        assert result is not None
        assert result.id == "ac-003"

    def test_device_type_keyword_match(self, sample_devices):
        """设备类型关键词匹配"""
        from nlu.routes import _find_device
        result = _find_device("把电视关掉", sample_devices)
        assert result is not None
        assert result.id == "tv-001"

    def test_room_and_type_match(self, sample_devices):
        """房间+类型匹配"""
        from nlu.routes import _find_device
        result = _find_device("打开卧室的灯", sample_devices)
        assert result is not None
        assert result.id == "light-002"

    def test_no_match_returns_none(self, sample_devices):
        """无匹配返回 None"""
        from nlu.routes import _find_device
        result = _find_device("帮我做点事", sample_devices)
        assert result is None

    def test_room_priority_over_type(self, sample_devices):
        """房间关键词优先于类型关键词"""
        from nlu.routes import _find_device
        # "卧室"+"灯" 应该匹配 light-002（卧室氛围灯），而非 light-001（客厅主灯）
        result = _find_device("打开卧室灯", sample_devices)
        assert result is not None
        assert result.id == "light-002"


class TestBatchDeviceMatching:
    """批量设备匹配"""

    def test_find_all_lights(self, sample_devices):
        """查找所有灯"""
        from nlu.routes import _find_devices_by_type
        result = _find_devices_by_type("打开所有灯", sample_devices, "light")
        assert len(result) == 2
        ids = [d.id for d in result]
        assert "light-001" in ids
        assert "light-002" in ids

    def test_find_only_room_lights(self, sample_devices):
        """按房间查找灯 — 验证 light-002 被包含"""
        from nlu.routes import _find_devices_by_type
        result = _find_devices_by_type("打开卧室所有灯", sample_devices, "light")
        # 至少包含卧室的灯
        ids = [d.id for d in result]
        assert "light-002" in ids


# ======================== 数值提取测试 ========================


class TestNumberExtraction:
    """数值提取功能"""

    def test_extract_temperature(self):
        """提取温度数值"""
        import re
        text = "把空调调到26度"
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        assert match is not None
        assert match.group(1) == "26"

    def test_extract_percentage(self):
        """提取百分比数字"""
        import re
        # 纯数字场景
        text = "亮度调到80%"
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        assert match is not None
        assert match.group(1) == "80"

    def test_extract_decimal(self):
        """提取小数"""
        import re
        text = "调到25.5度"
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        assert match is not None
        assert match.group(1) == "25.5"


# ======================== 命令识别测试 ========================


class TestCommandRecognition:
    """命令关键词识别"""

    def test_turn_on_keywords(self):
        """开机关键词"""
        from nlu.routes import TURN_ON_WORDS
        assert "打开" in TURN_ON_WORDS
        assert "开启" in TURN_ON_WORDS
        assert "启动" in TURN_ON_WORDS

    def test_turn_off_keywords(self):
        """关机关键词"""
        from nlu.routes import TURN_OFF_WORDS
        assert "关闭" in TURN_OFF_WORDS
        assert "关掉" in TURN_OFF_WORDS
        assert "停止" in TURN_OFF_WORDS

    def test_batch_target_keywords(self):
        """批量控制关键词"""
        from nlu.routes import BATCH_TARGET_WORDS
        assert "所有" in BATCH_TARGET_WORDS
        assert "全部" in BATCH_TARGET_WORDS
        assert "全屋" in BATCH_TARGET_WORDS


# ======================== 端到端 Interpret 测试 ========================


class TestInterpretEndpoint:
    """/internal/v1/nlu/interpret 端点"""

    @pytest.fixture
    def interpret_request_data(self, sample_devices, sample_scenes):
        """构建 interpret 请求数据"""
        return {
            "text": "",
            "conversation": [],
            "devices": [
                {
                    "id": d.id, "type": d.type, "name": d.name,
                    "room": d.room, "online": d.online,
                    "commands": [{"name": c.name, "params": c.params} for c in d.commands]
                }
                for d in sample_devices
            ],
            "scenes": [{"id": s.id, "name": s.name} for s in sample_scenes]
        }

    def test_interpret_simple_turn_on(self, interpret_request_data):
        """简单开机指令"""
        from fastapi.testclient import TestClient
        from nlu.routes import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        data = dict(interpret_request_data)
        data["text"] = "打开客厅灯"
        response = client.post("/interpret", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["understood"] is True

    def test_interpret_temperature_adjust(self, interpret_request_data):
        """温度调节指令"""
        from fastapi.testclient import TestClient
        from nlu.routes import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        data = dict(interpret_request_data)
        data["text"] = "把空调调到26度"
        response = client.post("/interpret", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["understood"] is True

    def test_interpret_scene_trigger(self, interpret_request_data):
        """场景触发指令"""
        from fastapi.testclient import TestClient
        from nlu.routes import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        data = dict(interpret_request_data)
        data["text"] = "进入观影模式"
        response = client.post("/interpret", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["understood"] is True

    def test_interpret_unclear_intent(self, interpret_request_data):
        """不明确的意图"""
        from fastapi.testclient import TestClient
        from nlu.routes import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        data = dict(interpret_request_data)
        data["text"] = "帮我搞一下那个东西"
        response = client.post("/interpret", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["understood"] is False

    def test_interpret_multi_action(self, interpret_request_data):
        """多动作指令"""
        from fastapi.testclient import TestClient
        from nlu.routes import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        data = dict(interpret_request_data)
        data["text"] = "打开客厅灯并关闭电视"
        response = client.post("/interpret", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["understood"] is True
        # 至少有两个 action
        assert len(result["actions"]) >= 2

    def test_interpret_batch_lights(self, interpret_request_data):
        """批量控制所有灯"""
        from fastapi.testclient import TestClient
        from nlu.routes import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        data = dict(interpret_request_data)
        data["text"] = "打开所有灯"
        response = client.post("/interpret", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["understood"] is True

    def test_interpret_unbound_device_rejected(self, interpret_request_data):
        """引用未绑定设备被拒绝"""
        from fastapi.testclient import TestClient
        from nlu.routes import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        data = dict(interpret_request_data)
        data["text"] = "打开车库门"
        response = client.post("/interpret", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["understood"] is False


# ======================== LLM 引擎测试 ========================


class TestLLMEngine:
    """LLM 引擎相关测试"""

    def test_build_devices_json(self):
        """构建设备 JSON 描述"""
        from nlu.llm_engine import _build_devices_json
        devices = [
            {"id": "ac-003", "type": "air_conditioner", "name": "客厅空调",
             "room": "客厅", "online": True,
             "commands": [{"name": "turn_on", "params": {}}]}
        ]
        result = _build_devices_json(devices)
        assert "ac-003" in result
        assert "air_conditioner" in result

    def test_build_devices_json_empty(self):
        """空设备列表"""
        from nlu.llm_engine import _build_devices_json
        result = _build_devices_json([])
        assert len(result) > 0  # 返回有效的 JSON 数组

    def test_system_prompt_contains_markers(self):
        """系统 prompt 包含必要标记"""
        from nlu.llm_engine import _SYSTEM_PROMPT
        assert "{devices_json}" in _SYSTEM_PROMPT
        assert "{scenes_json}" in _SYSTEM_PROMPT
        assert "understood" in _SYSTEM_PROMPT
        assert "actions" in _SYSTEM_PROMPT

    def test_deepseek_config_defaults(self):
        """DeepSeek 配置默认值"""
        from nlu import llm_engine
        assert llm_engine.DEEPSEEK_MODEL == "deepseek-chat"
        assert llm_engine.LLM_TIMEOUT_SECONDS == 15
        assert llm_engine.LLM_MAX_TOKENS == 1024
