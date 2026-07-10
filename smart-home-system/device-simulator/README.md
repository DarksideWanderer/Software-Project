# Smart Home Device Simulator

`device-simulator` provides C++ smart appliance processes for local integration. Each process connects to `backend-core` DeviceHub over TCP, registers its device ID, type and command capabilities, then waits for commands.

## Tech Stack

- C++20
- CMake
- POSIX socket APIs
- TCP JSON line protocol

## Supported Devices

| `--device` | Registered type | Default ID | Capabilities |
| --- | --- | --- | --- |
| `ac` | `air_conditioner` | `ac-001` | on/off, temperature |
| `light` | `light` | `light-001` | on/off, brightness, color |
| `tv` | `tv` | `tv-001` | on/off, channel, volume |
| `fridge` | `fridge` | `fridge-001` | on/off, temperature |
| `washer` | `washer` | `washer-001` | on/off, progress |
| `heater` | `water_heater` | `heater-001` | on/off, water temperature |
| `purifier` | `air_purifier` | `purifier-001` | on/off, speed, air quality |
| `curtain` | `curtain` | `curtain-001` | on/off, open percentage |
| `socket` | `socket` | `socket-001` | on/off |
| `robot` | `robot_vacuum` | `robot-001` | on/off, battery |

## Directory Structure

```text
device-simulator/
├── CMakeLists.txt
├── src/main.cpp
└── include/
    ├── core/
    │   ├── HubClient.h
    │   ├── CommandRegistry.h
    │   ├── Protocol.h
    │   └── Logger.h
    └── devices/
        ├── AirConditioner.h
        ├── AirConditionerAdapter.h
        ├── Light.h
        ├── LightAdapter.h
        ├── TV.h
        ├── TVAdapter.h
        ├── GenericDevice.h
        └── GenericDeviceAdapter.h
```

## Build

```bash
cd smart-home-system/device-simulator
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build
```

On Windows, use MSYS2 or another environment that provides POSIX socket headers such as `sys/socket.h`.

## Run

Start `backend-core` first so DeviceHub is listening on `127.0.0.1:9760`.

```bash
./build/simulator --device ac --id ac-003
./build/simulator --device ac --id ac-004
./build/simulator --device light --id light-001
./build/simulator --device tv --id tv-001
```

If `--id` is omitted, the simulator uses the default ID for that device type.

## Verify

```bash
curl http://127.0.0.1:8000/api/v1/devices/discover
```

After binding a discovered device in the web console, commands are sent through:

```http
POST /api/v1/devices/{device_id}/commands
```

## Notes

- Each appliance should run as a separate process.
- Device IDs must be unique in DeviceHub.
- If a cached device ID reconnects with a different type, `backend-core` marks it as a conflict and blocks control.

---
[中文文档](./README_zh.md)
