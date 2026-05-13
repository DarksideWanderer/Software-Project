# 智能家居设备仿真器

## 简介
模拟智能家居硬件设备（灯光、空调、传感器）和常用协议，实现无物理硬件环境下的协同开发。

## 技术栈
- **语言**: C++ 20
- **构建系统**: CMake
- **消息队列**: Mosquitto (MQTT 库)
- **测试**: Google Test (GTest)

## 目录结构
- `include/`: 头文件
- `src/core/`: 协议抽象
- `src/devices/`: 虚拟设备实现
- `tests/`: GTest 测试用例
- `scripts/`: 仿真控制脚本
