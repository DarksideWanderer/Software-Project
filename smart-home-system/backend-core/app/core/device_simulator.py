"""
DeviceHub — TCP 设备管理中心

启动 TCP 服务器，接收 C++ 设备进程的 TCP 连接。
设备连接后发送注册 JSON，Hub 记录后保持连接。
后续 REST API 通过该连接转发命令（带锁防止并发冲突）。
"""
import asyncio
import json
import logging
from typing import Dict

logger = logging.getLogger("DeviceHub")


class DeviceConnection:
    """单个设备的 TCP 连接（带读写锁）"""
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.info: dict = {}
        self._lock = asyncio.Lock()

    async def send_recv(self, data: str) -> str:
        """加锁写命令 + 读响应"""
        async with self._lock:
            self.writer.write((data + "\n").encode())
            await self.writer.drain()
            line = await self.reader.readline()
            return line.decode().strip()

    async def read_registration(self) -> str:
        """注册阶段：只读一次（无并发，不需锁）"""
        line = await self.reader.readline()
        return line.decode().strip()

    async def wait_closed(self):
        """阻塞直到连接断开"""
        try:
            await self.writer.wait_closed()
        except Exception:
            pass

    def close(self):
        try:
            self.writer.close()
        except Exception:
            pass


class DeviceHub:
    """全局设备管理中心"""

    def __init__(self, host: str = "0.0.0.0", port: int = 9760):
        self._host = host
        self._port = port
        self._devices: Dict[str, DeviceConnection] = {}
        self._registry: Dict[str, dict] = {}

    # ── 查询接口（供 API 调用） ──

    def list_devices(self) -> list:
        return [{
            "device_id": did,
            "device_type": info.get("type", "unknown"),
            "commands": [
                {"name": c["name"], "description": c.get("description", ""),
                 "params": c.get("params", [])}
                for c in info.get("commands", [])
            ],
            "state_fields": info.get("state_fields", {})
        } for did, info in self._registry.items()]

    async def send_command(self, device_id: str, command: str, params: dict = None) -> dict:
        conn = self._devices.get(device_id)
        if not conn:
            return {"success": False, "message": f"Device {device_id} not connected"}

        payload = json.dumps({"command": command, "params": params or {}})
        resp = await conn.send_recv(payload)
        try:
            return json.loads(resp)
        except json.JSONDecodeError:
            return {"success": False, "message": "Invalid response", "raw": resp}

    async def get_state(self, device_id: str) -> dict:
        return await self.send_command(device_id, "get_state")

    # ── TCP 服务器 ──

    async def start(self):
        server = await asyncio.start_server(
            self._handle_client, self._host, self._port
        )
        logger.info(f"DeviceHub listening on {self._host}:{self._port}")
        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        conn = DeviceConnection(reader, writer)
        addr = writer.get_extra_info('peername')
        logger.info(f"Device connected: {addr}")

        try:
            # 等待注册
            line = await conn.read_registration()
            if not line:
                return

            msg = json.loads(line)
            if msg.get("type") != "register":
                logger.warning(f"Expected register, got: {line[:100]}")
                return

            device = msg["device"]
            device_id = device["id"]
            device_type = device["type"]

            conn.info = device
            self._devices[device_id] = conn
            self._registry[device_id] = device

            logger.info(f"Registered: {device_type}:{device_id} "
                        f"({len(device.get('commands', []))} commands)")

            # 阻塞等待设备断开（不做任何读操作，避免和 send_command 冲突）
            await conn.wait_closed()

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Registration error: {e}")
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            conn.close()
            device_id = conn.info.get("id", "unknown")
            self._devices.pop(device_id, None)
            self._registry.pop(device_id, None)
            logger.info(f"Device disconnected: {device_id}")


hub = DeviceHub()


