# TTS 语音合成模块

## 概述

TTS（Text-To-Speech）模块负责将文本合成为语音，提供内部 API 供 `backend-core` 调用。当前实现采用**双引擎降级策略**：

1. **云端引擎** — 阿里云百炼 Qwen-TTS（DashScope SDK）
2. **本地降级** — pyttsx3（离线合成，仅支持 WAV 格式）

## API 接口

### 基础路径

```
POST /internal/v1/tts/speech
Content-Type: application/json
```

此接口为 **AI 服务内部接口**，仅允许 `backend-core` 调用，不直接对浏览器开放。

---

### 请求格式

```json
{
  "text": "卧室氛围灯已调到 35%。",
  "voice": "default",
  "format": "mp3"
}
```

#### 请求字段

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | 是 | — | 需要合成语音的文本 |
| `voice` | string | 否 | `"default"` | 音色名称（云端 DashScope 支持；本地降级忽略此参数） |
| `format` | string | 否 | `"mp3"` | 音频格式，支持 `mp3` / `wav` |

> **注意**：本地降级时 `pyttsx3` 仅支持 WAV 输出。若请求 `format` 不为 `wav`，日志会记录提示，但实际仍返回 WAV 文件。

---

### 成功响应

#### 云端 DashScope 成功

```json
{
  "status": "success",
  "audio_url": "https://dashscope.aliyuncs.com/...",
  "content_type": "audio/mpeg",
  "request_id": "a1b2c3d4-..."
}
```

#### 本地降级成功

```json
{
  "status": "success",
  "audio_url": "/internal/v1/tts/audio/a1b2c3d4.wav",
  "content_type": "audio/wav",
  "expires_at": "2026-06-18T12:30:00+08:00",
  "request_id": null
}
```

#### 响应字段

| 字段 | 类型 | 始终返回 | 说明 |
|------|------|----------|------|
| `status` | string | 是 | 固定为 `"success"` |
| `audio_url` | string | 是 | 音频文件的 URL（云端的绝对 URL 或本地的相对路径） |
| `content_type` | string | 是 | 音频的 MIME 类型（`audio/mpeg` / `audio/wav`） |
| `expires_at` | string | 仅本地 | ISO 8601 格式的过期时间（CST 时区），默认 30 分钟 |
| `request_id` | string | 否 | 云端返回的请求 ID；本地降级时为 `null` |
| `message` | string | 否 | 附加信息（当前未使用） |

#### MIME 类型映射

| `format` 请求值 | `content_type` 响应值 |
|-----------------|----------------------|
| `mp3` | `audio/mpeg` |
| `wav` | `audio/wav` |
| `ogg` | `audio/ogg` |
| `webm` | `audio/webm` |

---

### 错误响应

```json
{
  "detail": "语音合成失败（云端与本地均不可用）: ..."
}
```

| HTTP 状态码 | 场景 |
|-------------|------|
| `500` | 云端与本地均不可用（网络异常、SDK 缺失、本地引擎崩溃等） |

---

### 其他端点

#### TTS 模块健康检查

```http
GET /internal/v1/tts/health
```

响应：

```json
{
  "status": "ok",
  "module": "tts"
}
```

#### 静态音频文件获取

```
GET /internal/v1/tts/audio/{filename}
```

本地降级生成的音频文件通过 FastAPI `StaticFiles` 提供静态服务。音频文件默认在 30 分钟后过期并被后台任务清理。

---

## 工作流程

```
┌──────────────┐    POST /internal/v1/tts/speech    ┌──────────────────────┐
│ backend-core │ ──────────────────────────────────> │  TTS 模块            │
│              │                                     │                      │
│              │ <────────────────────────────────── │  1. 检查 API Key     │
│              │     audio_url / content_type        │     ↓                │
└──────────────┘                                     │  2. 有 Key？         │
                                                     │     ├── 是 → 调用     │
       ┌────────────────────────────────┐            │     │    DashScope    │
       │ 浏览器 / 前端请求 Audio URL    │            │     └── 否 → 本地     │
       │ 直接访问静态文件或云端地址      │            │          pyttsx3     │
       └───────────────┬────────────────┘            │     ↓                │
                       │                             │  3. 返回响应         │
                       ▼                             └──────────────────────┘
              ┌─────────────────┐
              │ 播放音频        │
              └─────────────────┘
```

## 配置

| 环境变量 | 必需 | 默认值 | 说明 |
|----------|------|--------|------|
| `DASHSCOPE_API_KEY` | 否 | — | 阿里云百炼 API Key；未设置时自动降级为本地合成 |

> 安全要求：API Key 仅保存在服务端环境变量中，前端不得获取或传递。

## 音频文件生命周期

| 项目 | 值 |
|------|-----|
| 存储目录 | `src/tts/generated_audio/` |
| 有效期限 | 30 分钟（`AUDIO_MAX_AGE_SECONDS = 1800`） |
| 清理间隔 | 每 10 分钟清理一次过期文件 |
| 支持格式 | `.wav`（本地）、`.mp3`（云端） |

后台协程 `cleanup_audio_background` 在应用启动时自动执行一次清理，之后每 10 分钟循环清理。

## 本地降级说明

- 使用 `pyttsx3` 库进行离线合成
- **仅支持 WAV 格式**，请求 `format` 为 `mp3` 时会输出 WAV 并在日志中记录提示
- 合成在独立线程池 `ThreadPoolExecutor` 中执行，不阻塞主协程
- 语音速率固定为 `150`

## 依赖

- `fastapi` — Web 框架
- `pyttsx3` — 本地语音合成引擎（降级用）
- `dashscope` — 阿里云百炼 SDK（可选，云端引擎用）
- `python-dotenv` — 环境变量加载

## 相关文档

- [FRONTEND_API_REQUIREMENTS.md](../../docs/FRONTEND_API_REQUIREMENTS.md) — 全量 API 契约（§8.3 TTS 合成、§7.4 TTS 回复）
- [AI 服务层 README](../README_zh.md) — AI 服务整体架构
