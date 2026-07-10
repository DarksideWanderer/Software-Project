# Sprint 1 - 项目基础架构与 API 契约完善

**时间范围**：第 1 个迭代周期（1 周）
**Sprint Goal**：确认 `web-console -> backend-core -> ai-service / DeviceHub -> device-simulator` 的真实架构，建立 API、设备模型、AI 内部接口和本地联调基础。

## 1. 背景与范围

本阶段以 `backend-core` FastAPI 为统一入口，浏览器只访问 `/api/v1`；`ai-service` 提供内部 ASR/NLU/TTS 接口；C++ `device-simulator` 通过 TCP 连接 `DeviceHub` 并注册设备能力。Sprint 1 的重点是确定这些模块之间的通信方式、API 契约和基础数据模型，为后续业务功能开发提供稳定基础。

## 2. User Stories

| ID | User Story | 优先级 | SP | Acceptance Criteria | 负责人 |
| --- | --- | --- | --- | --- | --- |
| US1-1 | 作为开发人员，我希望明确前端、主后端、AI 服务和设备模拟器的服务边界，以便各模块可以并行开发。 | P0 | 5 | 文档明确 Web 只访问 `backend-core`，AI key 只在 `ai-service` 服务端保存。 | 陈浩贤, 何亮, 徐子轩 |
| US1-2 | 作为后端开发人员，我希望确定稳定的 API 前缀，以便前端后续统一对接 `/api/v1`。 | P0 | 5 | `backend-core/app/api/v1` 聚合 devices、scenes、assistant、dashboard、audio 路由。 | 陈浩贤 |
| US1-3 | 作为 AI 开发人员，我希望建立内部 ASR/NLU/TTS 接口，以便主后端可以安全调用 AI 能力。 | P0 | 5 | `ai-service` 提供 `/internal/health`、ASR、NLU、TTS 内部接口。 | 何亮, 林子程, 杨志宸 |
| US1-4 | 作为设备模拟器开发人员，我希望模拟设备能够注册自身能力，以便后端可以根据能力转发命令。 | P0 | 8 | C++ simulator 连接 `DeviceHub :9760` 并发送 register JSON。 | 覃锐麟 |
| US1-5 | 作为前端开发人员，我希望先建立可运行的 Web 页面骨架，以便后续迭代承载设备、场景和助手功能。 | P1 | 3 | `web-console` 可静态访问，预留设备卡片、场景和助手区域。 | 徐子轩, 徐梓博 |

## 3. Product Backlog Items

| PBI | 内容 | 优先级 | SP | 依赖 |
| --- | --- | --- | --- | --- |
| PBI1-1 | 梳理实际架构与目录职责 | P0 | 3 | 无 |
| PBI1-2 | 建立 `backend-core` FastAPI 路由聚合与 CORS | P0 | 5 | PBI1-1 |
| PBI1-3 | 建立 AI 内部接口骨架与健康检查 | P0 | 5 | PBI1-1 |
| PBI1-4 | 建立 DeviceHub TCP 注册和命令协议 | P0 | 8 | PBI1-1 |
| PBI1-5 | 明确设备、命令、场景和家庭状态基础模型 | P0 | 5 | PBI1-2, PBI1-4 |
| PBI1-6 | 整理端口、环境变量和本地启动顺序 | P1 | 3 | PBI1-2, PBI1-3 |

## 4. 具体任务拆分

| 任务 | 描述 | 负责人 | SP |
| --- | --- | --- | --- |
| T1-1 | 阅读 `Plan.md`、`ARCHITECTURE.md`、`FRONTEND_API_REQUIREMENTS.md`，整理系统边界、接口需求和模块职责。 | 陈浩贤, 何亮, 徐子轩 | 2 |
| T1-2 | 设计 `/api/v1` 路由结构，保留 devices、scenes、assistant、dashboard、audio。 | 陈浩贤 | 3 |
| T1-3 | 设计 AI 请求/响应模型，明确 NLU 只输出动作计划。 | 何亮, 林子程 | 5 |
| T1-4 | 设计 DeviceHub TCP JSON 行协议和基础命令转发。 | 覃锐麟 | 5 |
| T1-5 | 定义设备能力字段：`id`、`type`、`commands`、`state_fields`、参数约束。 | 覃锐麟, 林子程 | 3 |
| T1-6 | 搭建 Web 静态入口和基础页面结构。 | 徐子轩, 徐梓博 | 3 |
| T1-7 | 整理本地运行说明：8000、8001、9760 和 Web 静态访问。 | 陈浩贤, 何亮, 徐子轩 | 2 |

## 5. 七名成员分工

| 成员 | 方向 | 本 Sprint 主要职责 |
| --- | --- | --- |
| 何亮 | AI | AI 服务接口边界、NLU 请求模型、内部健康检查。 |
| 杨志宸 | AI | TTS 接口契约、语音合成降级、音频文件生命周期和密钥隔离。 |
| 林子程 | AI | AI 服务接口、ASR/NLU/TTS 联调测试和接口文档整理。 |
| 陈浩贤 | 后端 | FastAPI 应用入口、路由聚合、CORS 和健康检查。 |
| 覃锐麟 | 后端 | DeviceHub TCP 协议和 C++ simulator 通信约定。 |
| 徐子轩 | 前端 | Web 控制台基础页面结构和 API 调用规划。 |
| 徐梓博 | 前端 | 基础视觉布局、导航、占位卡片和联调提示。 |

## 6. 任务优先级与工作量

| 优先级 | 内容 | 合计 SP |
| --- | --- | --- |
| P0 | 服务边界、API、AI 内部接口、DeviceHub、设备模型 | 28 |
| P1 | Web shell、运行说明、文档同步 | 8 |
| **总计** |  | **36** |

## 7. 依赖关系

- 前端依赖 `/api/v1` 和设备模型。
- NLU 依赖设备能力 Schema，本阶段仅完成接口和动作结构设计。
- C++ simulator 依赖 DeviceHub 先启动。
- 持久化只确定方向，实际缓存放到 Sprint 3。

## 8. Acceptance Criteria

- `backend-core` 能启动并提供 `/health`。
- `ai-service` 能启动并提供 `/internal/health`。
- DeviceHub 协议与 C++ 启动入口一致，明确当前使用 TCP 而不是 MQTT。
- 文档明确未实现用户认证、真实数据库、WebSocket 推送和生产权限。

## 9. Definition of Done

- API 路径、端口和模块边界写入文档。
- 核心字段命名在前端、后端、AI 之间保持一致。
- Sprint 1 的交付物聚焦架构、接口、数据模型和本地联调基础。

## 10. 测试与验收方案

- 访问 `GET /health` 检查 `backend-core`。
- 访问 `GET /internal/health` 检查 `ai-service`。
- 启动一个 simulator 后访问 `GET /api/v1/devices/raw`。
- 检查 `web-console` 静态资源能加载。

## 11. Sprint Review 预期成果

- 展示四模块架构和启动顺序。
- 展示基础健康检查。
- 说明后续 Sprint 以 TCP DeviceHub 和 Web 控制台为主线。

## 12. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| 模块边界理解不一致 | 后续接口对接返工 | 在 Sprint 1 固化服务边界、端口和 API 前缀。 |
| AI 与后端动作 Schema 不一致 | NLU 输出无法执行 | 林子程 与 陈浩贤 共同维护设备命令约束。 |
| Windows 编译环境差异 | 模拟器无法运行 | 说明 C++ simulator 使用 CMake 和 MSYS2/Linux 类环境。 |

## 13. Sprint Retrospective

本 Sprint 完成了四个核心模块的边界确认和基础联调规划。后续需要在此基础上逐步补充业务流程、状态缓存、场景系统和 AI 控制能力。
