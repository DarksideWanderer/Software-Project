"""
backend-core DeviceHub 单元测试
测试 core/device_simulator.py 中的 TCP 设备管理中心
"""
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestDeviceConnection:
    """DeviceConnection 类测试"""

    def test_init_stores_reader_writer(self):
        """初始化存储 reader 和 writer"""
        from app.core.device_simulator import DeviceConnection
        reader = MagicMock()
        writer = MagicMock()
        conn = DeviceConnection(reader, writer)
        assert conn.reader is reader
        assert conn.writer is writer
        assert conn.info == {}

    def test_close_calls_writer_close(self):
        """close 调用 writer.close"""
        from app.core.device_simulator import DeviceConnection
        writer = MagicMock()
        conn = DeviceConnection(MagicMock(), writer)
        conn.close()
        writer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_recv_exchanges_data(self):
        """send_recv 正确发送和接收数据"""
        from app.core.device_simulator import DeviceConnection
        reader = AsyncMock()
        reader.readline = AsyncMock(return_value=b'{"success":true}\n')
        writer = MagicMock()
        writer.drain = AsyncMock()
        writer.write = MagicMock()
        conn = DeviceConnection(reader, writer)
        result = await conn.send_recv('{"command":"turn_on"}')
        assert result == '{"success":true}'
        writer.write.assert_called()

    @pytest.mark.asyncio
    async def test_send_recv_handles_disconnect(self):
        """send_recv 处理连接断开"""
        from app.core.device_simulator import DeviceConnection
        reader = AsyncMock()
        reader.readline = AsyncMock(return_value=b"")
        writer = MagicMock()
        writer.drain = AsyncMock()
        writer.write = MagicMock()
        conn = DeviceConnection(reader, writer)
        with pytest.raises(ConnectionError):
            await conn.send_recv('{"command":"turn_on"}')

    @pytest.mark.asyncio
    async def test_read_registration(self):
        """读取设备注册信息"""
        from app.core.device_simulator import DeviceConnection
        reader = AsyncMock()
        reader.readline = AsyncMock(
            return_value=b'{"type":"register","device":{"id":"ac-003","type":"air_conditioner"}}\n'
        )
        conn = DeviceConnection(reader, MagicMock())
        line = await conn.read_registration()
        assert "ac-003" in line


class TestDeviceHub:
    """DeviceHub 类测试"""

    @pytest.fixture
    def hub(self):
        from app.core.device_simulator import DeviceHub
        return DeviceHub()

    def test_init_creates_empty_registry(self, hub):
        """初始化创建空注册表"""
        assert hub._registry == {}
        assert hub._devices == {}

    def test_list_devices_empty(self, hub):
        """空注册表返回空列表"""
        assert hub.list_devices() == []

    def test_list_devices_with_registered(self, hub):
        """有注册设备时返回列表"""
        hub._registry = {
            "ac-003": {"type": "air_conditioner", "description": "客厅空调"},
            "light-001": {"type": "light", "description": "主灯"}
        }
        hub._devices = {"ac-003": MagicMock()}
        devices = hub.list_devices()
        assert len(devices) == 2
        ac = [d for d in devices if d["device_id"] == "ac-003"][0]
        assert ac["connected"] is True
        light = [d for d in devices if d["device_id"] == "light-001"][0]
        assert light["connected"] is False

    @pytest.mark.asyncio
    async def test_send_command_device_not_connected(self, hub):
        """设备未连接时返回失败"""
        result = await hub.send_command("nonexistent", "turn_on")
        assert result["success"] is False
        assert "not connected" in result["message"]

    @pytest.mark.asyncio
    async def test_send_command_to_connected_device(self, hub):
        """向已连接设备发送命令成功"""
        conn = MagicMock()
        conn.send_recv = AsyncMock(return_value='{"success":true,"state":{"is_on":true}}')
        hub._devices["ac-003"] = conn
        result = await hub.send_command("ac-003", "turn_on", {})
        assert result["success"] is True
        assert result["state"]["is_on"] is True

    @pytest.mark.asyncio
    async def test_send_command_handles_disconnect(self, hub):
        """发送命令时连接断开，清理设备"""
        conn = MagicMock()
        conn.send_recv = AsyncMock(side_effect=ConnectionError("gone"))
        conn.close = MagicMock()
        hub._devices["ac-003"] = conn
        hub._registry["ac-003"] = {"type": "air_conditioner"}
        result = await hub.send_command("ac-003", "turn_on")
        assert result["success"] is False
        assert "ac-003" not in hub._devices

    def test_get_command_count(self, hub):
        """查询设备命令数量"""
        hub._registry["ac-003"] = {
            "type": "air_conditioner",
            "commands": [{"name": "turn_on"}, {"name": "turn_off"}, {"name": "set_temperature"}]
        }
        result = hub.get_command_count("ac-003")
        assert result["command_count"] == 3

    def test_get_command_count_unknown_device(self, hub):
        """查询未知设备命令返回 0"""
        result = hub.get_command_count("nonexistent")
        assert result["command_count"] == 0

    def test_get_command_schema(self, hub):
        """查询命令 schema"""
        hub._registry["ac-003"] = {
            "type": "air_conditioner",
            "commands": [
                {"name": "turn_on", "description": "打开空调", "params": []}
            ]
        }
        result = hub.get_command_schema("ac-003", "turn_on")
        assert result["command"]["name"] == "turn_on"
        assert result["command"]["description"] == "打开空调"

    def test_get_command_schema_unknown_command(self, hub):
        """查询未知命令 schema 返回提示"""
        hub._registry["ac-003"] = {"type": "air_conditioner", "commands": []}
        result = hub.get_command_schema("ac-003", "fly")
        assert "message" in result


class TestDeviceHubTCP:
    """DeviceHub TCP 服务器集成测试"""

    def test_hub_host_and_port(self):
        """Hub 配置正确的主机和端口"""
        from app.core.device_simulator import DeviceHub
        hub = DeviceHub(host="127.0.0.1", port=9999)
        assert hub._host == "127.0.0.1"
        assert hub._port == 9999

    def test_hub_default_port(self):
        """默认端口 9760"""
        from app.core.device_simulator import DeviceHub
        hub = DeviceHub()
        assert hub._port == 9760
