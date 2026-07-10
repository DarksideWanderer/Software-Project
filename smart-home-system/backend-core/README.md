# Smart Home Backend Core

`backend-core` is the main FastAPI service of the smart home system. It exposes `/api/v1` to the web console, starts DeviceHub for C++ simulators, persists home state, executes scenes, and proxies internal AI service calls.

## Responsibilities

- Serve the web console when `web-console` exists beside this directory.
- Start DeviceHub on TCP port `9760`.
- Discover currently connected simulator devices.
- Bind discovered devices into the user's home.
- Cache bound devices, display names, rooms, device states and user scenes in `data/home_state.json`.
- Reject duplicate binding, offline control and ID/type conflicts.
- Execute device commands and scene command batches.
- Call `ai-service` for ASR, NLU and TTS through internal HTTP APIs.

## Tech Stack

- Python 3.10+
- FastAPI
- httpx
- pytest
- Local JSON state file for course-demo persistence
- TCP DeviceHub for simulator communication

## Directory Structure

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

## Main APIs

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health check |
| `GET` | `/api/v1/dashboard` | Devices, candidates, scenes and summary |
| `GET` | `/api/v1/devices/discover` | Discover online unbound devices |
| `POST` | `/api/v1/devices/{id}/bind` | Bind a discovered device |
| `PATCH` | `/api/v1/devices/{id}` | Update device name and room |
| `DELETE` | `/api/v1/devices/{id}` | Remove a bound device |
| `POST` | `/api/v1/devices/{id}/commands` | Execute a validated device command |
| `POST` | `/api/v1/scenes` | Create a rule-based scene |
| `POST` | `/api/v1/scenes/natural` | Create a scene from natural language |
| `POST` | `/api/v1/scenes/{id}/execute` | Execute a scene |
| `POST` | `/api/v1/assistant/messages` | Text assistant command |
| `POST` | `/api/v1/assistant/voice` | Voice assistant command |

## Run

```bash
cd smart-home-system/backend-core
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000` to use the web console.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `AI_SERVICE_BASE_URL` | `http://127.0.0.1:8001` | Internal AI service base URL |

## Test

```bash
pytest tests -v
```

## Runtime State

`data/home_state.json` is created at runtime and stores:

- bound devices
- cached device states
- user-created scenes

The file is local course-demo persistence, not a production database.

---
[中文文档](./README_zh.md)
