# 智能家居中控系统

本项目是一个面向课程演示的智能家居中控系统，将静态 Web 控制台、FastAPI 主后端、内部 AI 服务和 C++ 家电模拟器串成完整闭环。

## 当前架构

```text
web-console
  -> backend-core /api/v1
    -> ai-service /internal/v1/asr|nlu|tts
    -> DeviceHub TCP :9760
      -> device-simulator 进程
```

浏览器只访问 `backend-core`。AI 模型密钥和供应商配置只放在 `ai-service/.env`。

## 模块说明

| 模块 | 路径 | 职责 |
| --- | --- | --- |
| Web 控制台 | `web-console` | 设备卡片、添加家电弹窗、设备详情抽屉、场景弹窗、助手面板 |
| 主后端 | `backend-core` | REST API、DeviceHub、家庭缓存、场景执行、AI 服务代理 |
| AI 服务 | `ai-service` | ASR、NLU、TTS 内部接口 |
| 设备模拟器 | `device-simulator` | C++ 家电进程，通过 TCP 注册 |
| 部署目录 | `deployment` | 本地部署说明和部署文件预留 |
| 移动端目录 | `app-mobile` | 预留模块；当前可运行客户端是 `web-console` |

## 主要功能

- 家庭初始为空，设备只有绑定后才进入家庭列表。
- 设备从当前在线的 C++ 模拟器进程中检索。
- 候选设备只在“添加家电”弹窗中展示，例如 `AC / ac-003`。
- 已绑定设备保存到 `backend-core/data/home_state.json`。
- 设备显示名称、房间、状态缓存和用户场景刷新后仍可恢复。
- 离线设备显示离线，不能控制，但仍可编辑或移除。
- 同 ID 不同类型设备会显示冲突并阻止控制。
- 保留回家、观影、离家预设场景。
- 用户可以通过规则或自然语言创建场景。
- 文本和语音助手由 `ai-service` 解析，最终由 `backend-core` 校验并执行。

## 本地运行

### 1. 启动 AI 服务

```bash
cd smart-home-system/ai-service
python -m pip install -r requirements.txt
uvicorn src.main:app --reload --port 8001
```

### 2. 启动主后端

```bash
cd smart-home-system/backend-core
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`backend-core` 会启动 `9760` 端口的 DeviceHub，并在 `http://127.0.0.1:8000` 托管 `web-console`。

### 3. 编译并启动设备模拟器

```bash
cd smart-home-system/device-simulator
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build

./build/simulator --device ac --id ac-003
./build/simulator --device ac --id ac-004
./build/simulator --device light --id light-001
```

Windows 下建议使用 MSYS2 环境运行模拟器，因为当前模拟器使用 POSIX socket 头文件。

## 常用检查

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/dashboard
curl http://127.0.0.1:8000/api/v1/devices/discover
curl http://127.0.0.1:8001/internal/health
```

## 测试命令

```bash
cd smart-home-system/web-console
node --check app.js

cd ../backend-core
pytest tests -v

cd ../ai-service
pytest tests -v

cd ../device-simulator
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build
```

## 说明

- `backend-core/data/home_state.json` 是运行时状态文件。
- `ai-service/.env` 用于本地 AI 供应商配置。
- 新增设备类型时，需要同时补充后端设备元数据和模拟器启动映射。
- 自然语言解析结果必须经过 `backend-core` 校验后才会执行。
