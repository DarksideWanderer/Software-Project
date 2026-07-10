# Smart Home System

This project is a course-demo smart home control system. It connects a static web console, a FastAPI backend, an internal AI service, and C++ device simulators into one runnable loop.

## Current Architecture

```text
web-console
  -> backend-core /api/v1
    -> ai-service /internal/v1/asr|nlu|tts
    -> DeviceHub TCP :9760
      -> device-simulator processes
```

The browser only talks to `backend-core`. API keys and AI provider configuration stay in `ai-service/.env`.

## Modules

| Module | Path | Role |
| --- | --- | --- |
| Web console | `web-console` | Device cards, add-device modal, device drawer, scene modal, assistant panel |
| Backend core | `backend-core` | REST API, DeviceHub, home cache, scene execution, AI service proxy |
| AI service | `ai-service` | ASR, NLU and TTS internal APIs |
| Device simulator | `device-simulator` | C++ device processes registered through TCP |
| Deployment | `deployment` | Local deployment notes and reserved deployment files |
| Mobile app | `app-mobile` | Reserved module; current runnable client is `web-console` |

## Main Features

- Empty home by default; devices appear only after user binding.
- Device discovery from currently connected C++ simulator processes.
- Candidate devices are shown in the add-device modal, for example `AC / ac-003`.
- Bound devices are cached in `backend-core/data/home_state.json`.
- Device name, room, cached state and user scenes survive page refresh.
- Offline devices are labeled offline and cannot be controlled, but can still be edited or removed.
- ID/type conflicts are detected and blocked.
- Built-in scenes include home, movie and away.
- User scenes can be created by rules or natural language.
- Text and voice assistant commands are parsed by `ai-service` and executed by `backend-core`.

## Run Locally

### 1. Start AI service

```bash
cd smart-home-system/ai-service
python -m pip install -r requirements.txt
uvicorn src.main:app --reload --port 8001
```

### 2. Start backend core

```bash
cd smart-home-system/backend-core
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`backend-core` starts DeviceHub on TCP port `9760` and serves `web-console` at `http://127.0.0.1:8000`.

### 3. Build and start device simulators

```bash
cd smart-home-system/device-simulator
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build

./build/simulator --device ac --id ac-003
./build/simulator --device ac --id ac-004
./build/simulator --device light --id light-001
```

On Windows, use an MSYS2 environment for the simulator because it uses POSIX socket headers.

## Useful Checks

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/dashboard
curl http://127.0.0.1:8000/api/v1/devices/discover
curl http://127.0.0.1:8001/internal/health
```

## Test Commands

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

## Notes

- `backend-core/data/home_state.json` is runtime state.
- `ai-service/.env` holds local AI provider configuration.
- New device types should be added to both backend device metadata and simulator startup mapping.
- Natural language output is always validated by `backend-core` before execution.
