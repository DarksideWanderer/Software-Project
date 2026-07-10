# 智能家居设备模拟器

`device-simulator` 提供本地联调用的 C++ 智能家电进程。每个进程通过 TCP 连接到 `backend-core` 的 DeviceHub，注册设备 ID、设备类型和命令能力，然后等待主后端下发控制命令。

## 技术栈

- C++20
- CMake
- POSIX socket API
- TCP JSON 行协议

## 支持设备

| `--device` | 注册类型 | 默认 ID | 能力 |
| --- | --- | --- | --- |
| `ac` | `air_conditioner` | `ac-001` | 开关、温度 |
| `light` | `light` | `light-001` | 开关、亮度、色温 |
| `tv` | `tv` | `tv-001` | 开关、频道、音量 |
| `fridge` | `fridge` | `fridge-001` | 开关、冷藏温度 |
| `washer` | `washer` | `washer-001` | 开关、洗涤进度 |
| `heater` | `water_heater` | `heater-001` | 开关、水温 |
| `purifier` | `air_purifier` | `purifier-001` | 开关、风速、空气质量 |
| `curtain` | `curtain` | `curtain-001` | 开关、开合百分比 |
| `socket` | `socket` | `socket-001` | 开关 |
| `robot` | `robot_vacuum` | `robot-001` | 开关、电量 |

## 目录结构

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

## 编译

```bash
cd smart-home-system/device-simulator
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build
```

Windows 下建议使用 MSYS2 或其他提供 POSIX socket 头文件的环境，例如 `sys/socket.h`。

## 运行

先启动 `backend-core`，确保 DeviceHub 已监听 `127.0.0.1:9760`。

```bash
./build/simulator --device ac --id ac-003
./build/simulator --device ac --id ac-004
./build/simulator --device light --id light-001
./build/simulator --device tv --id tv-001
```

不传 `--id` 时，模拟器会使用该设备类型的默认 ID。

## 验证

```bash
curl http://127.0.0.1:8000/api/v1/devices/discover
```

设备在前端绑定后，主后端通过以下接口发送控制命令：

```http
POST /api/v1/devices/{device_id}/commands
```

## 说明

- 每个家电建议单独启动一个进程。
- DeviceHub 中设备 ID 必须唯一。
- 如果缓存中的设备 ID 以不同类型重新连接，`backend-core` 会标记冲突并阻止控制。
