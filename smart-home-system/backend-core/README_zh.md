# 智能家居主后端

`backend-core` 是智能家居系统的 FastAPI 主服务。它向 Web 控制台提供 `/api/v1`，启动 DeviceHub 接收 C++ 模拟器连接，保存家庭状态，执行场景，并代理内部 AI 服务调用。

## 职责

- 在相邻目录存在 `web-console` 时托管前端静态资源。
- 启动 `9760` 端口的 DeviceHub TCP 服务。
- 检索当前在线的模拟器设备。
- 将检索到的候选设备绑定到用户家庭。
- 将已绑定设备、显示名称、房间、设备状态和用户场景保存到 `data/home_state.json`。
- 阻止重复绑定、离线控制和 ID 类型冲突。
- 执行设备命令和场景批量命令。
- 通过内部 HTTP 调用 `ai-service` 的 ASR、NLU、TTS。

## 技术栈

- Python 3.10+
- FastAPI
- httpx
- pytest
- 本地 JSON 状态文件
- TCP DeviceHub 设备通信

## 目录结构

```text
backend-core/
├── app/
│   ├── main.py
│   ├── api/v1/
│   │   ├── dashboard.py
│   │   ├── devices.py
│   │   ├── scenes.py
│   │   ├── assistant.py
│   │   ├── audio.py
│   │   └── commands.py
│   ├── core/device_simulator.py
│   ├── schemas/device.py
│   └── services/home_orchestrator.py
├── data/
├── tests/
└── requirements.txt
```

## 主要接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 后端健康检查 |
| `GET` | `/api/v1/dashboard` | 设备、候选设备、场景和统计 |
| `GET` | `/api/v1/devices/discover` | 检索在线且未绑定设备 |
| `POST` | `/api/v1/devices/{id}/bind` | 绑定设备 |
| `PATCH` | `/api/v1/devices/{id}` | 修改设备名称和房间 |
| `DELETE` | `/api/v1/devices/{id}` | 移除已绑定设备 |
| `POST` | `/api/v1/devices/{id}/commands` | 执行校验后的设备命令 |
| `POST` | `/api/v1/scenes` | 创建规则场景 |
| `POST` | `/api/v1/scenes/natural` | 根据自然语言创建场景 |
| `POST` | `/api/v1/scenes/{id}/execute` | 执行场景 |
| `POST` | `/api/v1/assistant/messages` | 文本助手 |
| `POST` | `/api/v1/assistant/voice` | 语音助手 |

## 运行

```bash
cd smart-home-system/backend-core
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 `http://127.0.0.1:8000` 可打开 Web 控制台。

## 配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `AI_SERVICE_BASE_URL` | `http://127.0.0.1:8001` | 内部 AI 服务地址 |

## 测试

```bash
pytest tests -v
```

## 运行时状态

`data/home_state.json` 会在运行时创建，用于保存：

- 已绑定设备
- 设备状态缓存
- 用户创建的场景

该文件用于课程演示中的轻量持久化，不是生产数据库。
