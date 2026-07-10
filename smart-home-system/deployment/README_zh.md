# 部署说明

本目录用于放置部署相关文件。当前项目主要以本地开发/演示方式运行，涉及四类进程：

1. `ai-service`，端口 `8001`
2. `backend-core`，端口 `8000`
3. DeviceHub TCP 服务，端口 `9760`，由 `backend-core` 启动
4. 一个或多个 `device-simulator` C++ 设备进程

## 当前部署方式

当前已验证方式是本地启动。`docker/` 目录作为部署准备保留，实际运行流程以项目根 README 和各模块 README 为准。

## 本地启动顺序

```bash
cd smart-home-system/ai-service
uvicorn src.main:app --reload --port 8001

cd ../backend-core
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

cd ../device-simulator
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build
./build/simulator --device ac --id ac-003
```

访问：

```text
http://127.0.0.1:8000
```

## 环境配置

| 项 | 位置 | 说明 |
| --- | --- | --- |
| AI 供应商配置 | `../ai-service/.env` | 本地密钥和供应商设置 |
| 后端 AI 地址 | `AI_SERVICE_BASE_URL` | 默认 `http://127.0.0.1:8001` |
| 家庭状态 | `../backend-core/data/home_state.json` | 已绑定设备和场景的运行时缓存 |
