# 全屋智能后端核心

## 简介
全屋智能系统的中央编排层，基于 FastAPI 构建。负责管理业务逻辑、设备状态（影子库）以及 MQTT 消息路由。

## 技术栈
- **语言**: Python 3.10+
- **框架**: FastAPI
- **ORM**: Tortoise-ORM / SQLAlchemy
- **缓存/状态**: Redis (设备影子)
- **消息队列**: MQTT (Paho-MQTT)

## 目录结构
- `app/api/`: 接口路由
- `app/core/`: 核心配置、安全与设置
- `app/models/`: 数据库模型
- `app/services/`: 业务逻辑与 MQTT 处理
- `tests/`: 测试套件
