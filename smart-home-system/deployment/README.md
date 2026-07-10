# Deployment Notes

This directory is reserved for deployment-related files. The current project is primarily run locally with four services:

1. `ai-service` on port `8001`
2. `backend-core` on port `8000`
3. DeviceHub TCP server on port `9760`, started by `backend-core`
4. One or more `device-simulator` C++ processes

## Current Deployment Mode

The current verified mode is local development/demo startup. The `docker/` directory exists for deployment preparation, but the runnable flow should follow the root project README and module README files.

## Local Startup Order

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

Open:

```text
http://127.0.0.1:8000
```

## Environment

| Item | Location | Description |
| --- | --- | --- |
| AI provider config | `../ai-service/.env` | Local keys and provider settings |
| Backend AI URL | `AI_SERVICE_BASE_URL` | Defaults to `http://127.0.0.1:8001` |
| Home state | `../backend-core/data/home_state.json` | Runtime cache for bound devices and scenes |

---
[中文文档](./README_zh.md)
