# Smart Home Backend Core

## Introduction
The central orchestration layer of the Smart Home System, built with FastAPI. It manages business logic, device states (Shadow), and MQTT message routing.

## Tech Stack
- **Language**: Python 3.10+
- **Framework**: FastAPI
- **ORM**: Tortoise-ORM / SQLAlchemy
- **Cache/State**: Redis (Device Shadow)
- **Messaging**: MQTT (Paho-MQTT)

## Directory Structure
- `app/api/`: API routes (v1, v2)
- `app/core/`: Security, config, settings
- `app/models/`: Database models
- `app/services/`: Business logic, MQTT handlers
- `tests/`: Pytest suite

---
[中文版文档入口](./README_zh.md)
