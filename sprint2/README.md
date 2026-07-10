# Sprint 2 - 基础业务功能与前后端联调

**时间范围**：第 2 个迭代周期（1 周）
**Sprint Goal**：完成最小可用的设备控制流程：已注册设备能够展示、查看状态、执行基本控制，并让文本/语音助手打通 AI 服务和后端执行链路。

## 1. 背景与范围

Sprint 1 已确认服务边界。本 Sprint 基于 `backend-core/app/services/home_orchestrator.py`、`DeviceHub` 和 `web-console/app.js` 完成基础业务闭环。设备以空调、灯、电视为主要 MVP；家庭和房间先使用轻量字段，不引入真实账号系统。

## 2. User Stories

| ID | User Story | 优先级 | SP | Acceptance Criteria | 负责人 |
| --- | --- | --- | --- | --- | --- |
| US2-1 | 作为用户，我希望在首页看到家电概览，以便快速了解当前设备状态。 | P0 | 5 | `/api/v1/dashboard` 返回 devices、scenes、summary；前端渲染设备卡片。 | BE-1, FE-1 |
| US2-2 | 作为用户，我希望能够控制单个家电，以便执行开关、温度、亮度等基础操作。 | P0 | 8 | 前端详情抽屉调用 `POST /api/v1/devices/{id}/commands`，后端返回最新状态。 | BE-2, FE-2 |
| US2-3 | 作为开发人员，我希望设备模拟器返回真实状态和命令结果，以便前端展示以后端结果为准。 | P0 | 5 | DeviceHub 可转发 `turn_on`、`turn_off`、`get_state` 和参数命令。 | BE-2 |
| US2-4 | 作为用户，我希望可以输入文字指令控制家电，以便用自然语言完成常见操作。 | P1 | 5 | `/api/v1/assistant/messages` 调用 NLU 并执行 actions。 | AI-1, BE-1, FE-1 |
| US2-5 | 作为用户，我希望语音输入与文字输入复用同一控制流程，以便获得一致的交互体验。 | P1 | 5 | `/api/v1/assistant/voice` 上传音频到 ASR 后复用 NLU 和执行链路。 | AI-2, FE-2 |

## 3. Product Backlog Items

| PBI | 内容 | 优先级 | SP | 依赖 |
| --- | --- | --- | --- | --- |
| PBI2-1 | Dashboard 聚合接口与摘要字段 | P0 | 5 | Sprint 1 |
| PBI2-2 | 设备详情、状态读取和基础控制 API | P0 | 8 | DeviceHub |
| PBI2-3 | 设备卡片、详情抽屉和控制控件 | P0 | 8 | PBI2-1, PBI2-2 |
| PBI2-4 | AI NLU 文本助手 | P1 | 5 | AI 内部接口 |
| PBI2-5 | ASR/TTS 语音助手链路 | P1 | 8 | PBI2-4 |

## 4. 具体任务拆分

| 任务 | 描述 | 负责人 | SP |
| --- | --- | --- | --- |
| T2-1 | 在 `home_orchestrator` 中聚合设备状态、能力、显示名称、房间和摘要。 | BE-1 | 5 |
| T2-2 | 在 `devices.py` 中提供产品化命令路径 `/devices/{id}/commands`。 | BE-2 | 3 |
| T2-3 | 完成空调、灯、电视三类设备的前端控件映射。 | FE-2 | 5 |
| T2-4 | 完成设备卡片、详情抽屉、开关、滑块和错误 toast。 | FE-1, FE-2 | 8 |
| T2-5 | 实现 NLU 规则：设备名称、房间、类型关键词、数值参数。 | AI-1, AI-3 | 5 |
| T2-6 | 实现 DeepSeek LLM fallback 的 prompt、JSON 提取和动作校验。 | AI-2 | 5 |
| T2-7 | 对接 `/assistant/messages` 和 `/assistant/voice`。 | BE-1, AI-1 | 5 |

## 5. 七名成员分工

| 成员 | 方向 | 本 Sprint 主要职责 |
| --- | --- | --- |
| AI-1 | AI | NLU 规则引擎和基础用例。 |
| AI-2 | AI | DeepSeek fallback、输出校验和失败降级。 |
| AI-3 | AI | 设备动作映射测试数据，参与 ASR/TTS 联调。 |
| BE-1 | 后端 | 聚合层、assistant 文本链路和 dashboard。 |
| BE-2 | 后端 | DeviceHub 命令转发、状态读取和模拟器联调。 |
| FE-1 | 前端 | 主页布局、设备卡片、摘要区和助手面板。 |
| FE-2 | 前端 | 详情抽屉、控制控件、录音上传和错误提示。 |

## 6. 任务优先级与工作量

| 优先级 | 内容 | 合计 SP |
| --- | --- | --- |
| P0 | dashboard、设备展示、基础控制、模拟器闭环 | 29 |
| P1 | 文本/语音助手、TTS 回复入口、错误提示 | 21 |
| **总计** |  | **50** |

## 7. 依赖关系

- 前端控制依赖设备 `capabilities`。
- assistant 执行依赖 NLU 返回 `device_command` 或 `scene` action。
- 语音助手依赖浏览器录音权限和 ASR 服务。

## 8. Acceptance Criteria

- 首页可展示至少空调、灯、电视中的已连接设备。
- 详情抽屉可执行开关和至少一个参数控制。
- 后端返回执行后的最新状态，前端以服务端状态刷新。
- 文本助手能解析“打开客厅灯”“把空调调到 26 度”。
- AI 服务不可用时，手动控制仍可使用并显示错误。

## 9. Definition of Done

- 前端不直接调用 `ai-service`。
- 后端校验命令名和参数。
- 关键联调路径有手动验收步骤。

## 10. 测试与验收方案

- `GET /api/v1/dashboard` 返回 devices、scenes、summary。
- `POST /api/v1/devices/{id}/commands` 对空调、灯、电视执行命令。
- `POST /internal/v1/nlu/interpret` 验证单设备、数值调节和模糊指令。
- 前端运行 `node --check app.js`。
- C++ 运行 `cmake --build build`。

## 11. Sprint Review 预期成果

- 展示 Web 控制台设备卡片和详情控制。
- 展示文本助手控制设备。
- 展示语音上传到 ASR 后复用同一执行链路。

## 12. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| NLU 规则简单 | 复杂表达无法解析 | 保留 LLM fallback，Sprint 4 扩展多动作。 |
| 模拟器断开状态滞后 | 用户误以为在线 | 命令失败后移除连接并返回最新状态。 |
| 前端乐观状态错误 | 与后端不一致 | 所有控制后使用后端响应刷新。 |

## 13. Sprint Retrospective

本 Sprint 建立了第一个可用闭环：Web 控制台通过后端控制模拟设备，AI 文本与语音入口开始接入。遗留问题是设备仍偏预置，缺少用户主动发现、绑定和持久化流程。
