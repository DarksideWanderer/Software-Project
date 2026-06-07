# 全屋智能中控 · Web 管理后台

基于 Vue 3 + Vite + Element Plus + Pinia 构建的全屋智能家电中控前端。
界面采用深浅双主题与玻璃拟态设计，简洁且具备高级感。

## 核心功能
- 总控面板：概览全部家电与大致状态、室内环境、快捷场景，并提供添加入口。
- 设备详情：点击卡片进入；按"能力模型"自动渲染对应控件，适配所有通用家电分类。
- 设备配对：向导式模拟配对（扫描发现 → 命名分配房间 → 连接 → 完成）。
- 房间视图：按空间归类管理设备。
- 语音控制：浏览器麦克风(Web Speech API)实时识别中文语音，解析为操控指令并执行；不支持时可用文本输入回退。
- AI 语义理解：可选接入大模型(LLM)做"文本→指令"解析，以设备命令自省 schema 作为接地上下文；不可用时自动回退内置规则解析。
- 数据源：本地演示 / 实时后端双模式，可对接队友的 FastAPI DeviceHub 真实设备。
- 设置：深浅主题、数据源、AI 配置、服务地址、演示数据恢复。

## 数据源与后端对接
- 本地演示：设备数据保存在浏览器，离线可用。
- 实时后端：对接 `proj/feature-cpp` 分支的 FastAPI DeviceHub。设置页一键连接，自动拉取设备、状态与命令清单。
  - 适配层：`src/api/backend.js`(真实端点) + `src/utils/deviceMapping.js`(类型/状态/命令双向映射)。
  - 端点契约：`GET /devices`、`GET /devices/{id}/state`、`POST /devices/{id}/command`、`GET /devices/{id}/commands/*`。
  - 当前后端支持灯光、空调、电视三类设备。

## AI 语义理解（语音 → 指令）
- 在设置页开启"AI 语义理解"，支持两种模式：
  - 后端 / ai-service：POST `{text, devices}` 到 `/api/v1/ai/voice-command`(可改)，由后端 LLM 返回结构化指令。
  - OpenAI 兼容端点：浏览器直连 `/chat/completions`，需填模型与 API Key（注意 CORS）。
- 关键设计：把每个设备的"可用命令 schema"作为接地上下文喂给模型，模型只能生成合法命令。
- 未启用或调用失败时，自动回退到内置规则解析(`src/utils/nlu.js`)，保证可用。

## 语音指令示例
"打开客厅的灯"、"把客厅空调调到26度"、"客厅灯调亮一点"、"关闭电视"、"打开窗帘"、"锁门"、"电视音量调到30"、"回家模式"。

## 目录结构
- `src/data/catalog.js` —— 通用家电分类与能力模型
- `src/stores/devices.js` —— 设备状态管理（本地持久化 + 实时后端数据源）
- `src/api/backend.js` —— 队友后端真实接口封装
- `src/api/aiCommand.js` —— LLM 语义理解客户端
- `src/utils/deviceMapping.js` —— 前后端模型双向映射
- `src/utils/nlu.js` —— 内置中文规则解析（回退）
- `src/composables/` —— useTheme / usePairing / useSpeech / useAIConfig
- `src/views/` —— Dashboard / Rooms / VoiceControl / DeviceDetail / Settings

## 本地运行
```bash
cd smart-home-system/web-frontend
npm install
npm run dev      # http://localhost:5173 ，开发代理 /api -> http://localhost:8000
npm run build
```
