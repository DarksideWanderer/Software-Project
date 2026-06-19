# ASR 语音识别模块

## 1. 模块定位

ASR（Automatic Speech Recognition）模块负责将用户上传的语音音频转写为文本，供下游 NLU 模块进行语义理解。

本模块只做语音转文字：

- 不进行语义理解或意图解析；
- 不直接控制设备；
- 不访问数据库；
- 不生成设备指令。

ASR 的输出格式以 `FRONTEND_API_REQUIREMENTS.md` 中 `§8.1 ASR 语音转写` 为准，核心字段为：

```json
{
  "text": "打开客厅灯",
  "language": "zh-CN",
  "confidence": 0.95,
  "duration_ms": 1200,
  "request_id": "uuid"
}
```

## 2. 双引擎降级策略

| 优先级 | 引擎 | 说明 | 状态 |
|--------|------|------|------|
| 1（主） | **讯飞 IAT API** | 云端语音听写，WebSocket 协议，16kHz 16bit mono PCM | ✅ 已接入 |
| 2（降级） | **Mock 引擎** | 确定性模拟转写，用于开发测试 | ✅ 可用 |

### 2.1 引擎选择逻辑

```
if 讯飞 API Key 已配置 AND 未设置 ASR_FORCE_MOCK:
    → 使用讯飞 IAT 引擎
elif 讯飞转写失败（网络/超时/服务端错误）:
    → 自动降级到 Mock 引擎
else:
    → 直接使用 Mock 引擎
```

- 设置环境变量 `ASR_FORCE_MOCK=true` 可强制使用 Mock 引擎（测试用）。
- 讯飞 API 配置通过 `.env` 文件注入：`IFLYTEK_APP_ID`、`IFLYTEK_API_KEY`、`IFLYTEK_API_SECRET`。

## 3. 文件结构

```text
asr/
├── __init__.py         # 导出 FastAPI router
├── routes.py           # ASR 路由、请求校验、Mock 引擎、错误响应
├── iflytek_engine.py   # 讯飞 IAT WebSocket 引擎、音频标准化
└── README.md           # 模块说明文档
```

### 3.1 routes.py

`routes.py` 是 ASR 主入口文件，包含：

- **FastAPI 路由** — `POST /internal/v1/asr/transcriptions`（主端点）、`GET /ai/asr/health`（健康检查）、`POST /ai/asr/transcribe`（已废弃兼容端点）。
- **请求校验** — `_validate_and_read_audio()` 对上传文件进行 MIME 类型、大小（≤10MB）、时长（≤30s）、最小内容（≥100 bytes）四重校验，优先解析 WAV 头获取真实参数。
- **Mock 引擎** — `_mock_transcribe()` 基于音频字节哈希值返回确定性模拟结果。
- **错误响应构建器** — `_error_response()` 生成符合统一错误格式的 JSON 响应。

### 3.2 iflytek_engine.py

`iflytek_engine.py` 是讯飞 IAT 引擎实现，包含：

| 函数 | 说明 |
|------|------|
| `engine_available()` | 检查讯飞 API 凭证是否已配置 |
| `transcribe()` | 异步主入口：标准化音频 → WebSocket 转写 |
| `_normalize_audio()` | 音频标准化流水线（WAV 解析 → 重采样 → 立体声转单声道 → 位深转换） |
| `_parse_wav_info()` | 解析 WAV 头，提取 sample_rate / channels / bits_per_sample / PCM 数据 |
| `_resample_pcm()` | 纯 Python 线性插值重采样（任意采样率 → 16kHz） |
| `_convert_stereo_to_mono()` | 立体声转单声道（L+R 平均） |
| `_transcribe_websocket()` | WebSocket 连接讯飞 IAT API，发送音频帧并收集转写结果 |
| `_build_auth_url()` | 构建讯飞 API 鉴权 URL（HMAC-SHA256 签名） |

#### 音频标准化流水线

```
输入 WAV（任意采样率/声道/位深）
    │
    ├─ 1. _parse_wav_info()   → 解析 WAV 头，提取原始参数
    ├─ 2. _resample_pcm()     → 重采样至 16kHz（线性插值）
    ├─ 3. _convert_stereo_to_mono() → 立体声 → 单声道
    ├─ 4. 位深转换             → 8/24/32-bit → 16-bit
    │
    ▼
输出: 16kHz 16-bit mono PCM（讯飞 IAT 标准格式）
```

## 4. API 接口

### 基础路径

```
POST /internal/v1/asr/transcriptions
Content-Type: multipart/form-data
```

此接口为 **AI 服务内部接口**，仅允许 `backend-core` 调用，不直接对浏览器开放。

---

### 请求格式

```http
POST /internal/v1/asr/transcriptions
Content-Type: multipart/form-data; boundary=----Boundary

------Boundary
Content-Disposition: form-data; name="audio"; filename="recording.wav"
Content-Type: audio/wav

<audio binary data>
------Boundary
Content-Disposition: form-data; name="language"

zh-CN
------Boundary
Content-Disposition: form-data; name="request_id"

550e8400-e29b-41d4-a716-446655440000
------Boundary--
```

#### 请求字段

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `audio` | file | **是** | — | 音频文件，支持格式见下方 |
| `language` | string | 否 | `"zh-CN"` | 音频语言标识 |
| `request_id` | string | 否 | 自动生成 UUID | 请求追踪 ID，用于跨服务排查 |

#### 支持的音频格式

| MIME 类型 | 说明 |
|-----------|------|
| `audio/wav` | WAV 格式（PCM），推荐 |
| `audio/wave` | WAV 别名 |
| `audio/x-wav` | WAV 别名 |
| `audio/webm` | WebM 容器 |
| `audio/webm;codecs=opus` | WebM + Opus 编码 |
| `audio/ogg` | OGG 容器 |
| `audio/ogg;codecs=opus` | OGG + Opus 编码 |

> **注意**：非 WAV 格式当前仅做 MIME 校验放行，转写时假定为 16kHz 16bit mono PCM。WebM/OGG 中的 Opus 编码需额外解码，当前版本暂未实现，建议前端统一录制 WAV 格式。

---

### 成功响应

```json
{
  "text": "帮我把空调调到26度",
  "language": "zh-CN",
  "confidence": 0.92,
  "duration_ms": 1499,
  "request_id": "483e6533-2467-4ae0-b0a9-571575b308af",
  "engine": "iflytek",
  "processing_ms": 1499
}
```

#### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 转写后的文本 |
| `language` | string | 识别语言 |
| `confidence` | float (0~1) | 置信度，Mock 引擎固定 ~0.85~1.0 |
| `duration_ms` | int | 音频时长（毫秒） |
| `request_id` | string | 请求追踪 ID |
| `engine` | string | 实际使用的引擎：`"iflytek"` 或 `"mock"` |
| `processing_ms` | int | 实际处理耗时（毫秒） |

---

### 错误响应

所有错误遵循统一格式：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "人类可读描述",
    "details": {},
    "request_id": "uuid"
  }
}
```

#### 错误码一览

| HTTP 状态码 | 错误码 | 触发条件 |
|-------------|--------|----------|
| `415` | `UNSUPPORTED_AUDIO_FORMAT` | MIME 类型不在白名单中 |
| `413` | `AUDIO_TOO_LARGE` | 文件大小超过 10 MB |
| `422` | `SPEECH_NOT_DETECTED` | 文件小于 100 字节（无有效语音） |
| `422` | `AUDIO_TOO_LONG` | 音频时长超过 30 秒 |
| `422` | `UNPROCESSABLE_CONTENT` | 缺少 `audio` 字段 |
| `503` | `SERVICE_UNAVAILABLE` | 讯飞引擎不可用且未启用 Mock |

---

### 健康检查

```http
GET /ai/asr/health
```

```json
{
  "status": "ok",
  "module": "asr",
  "engine": "iflytek"
}
```

`engine` 字段指示当前激活的引擎：`"iflytek"` 或 `"mock"`。

## 5. 约束与限制

| 约束项 | 值 | 说明 |
|--------|-----|------|
| 最大文件大小 | 10 MB | 超过返回 413 |
| 最大音频时长 | 30 秒 | 超过返回 422，WAV 格式自动解析真实时长 |
| 最小音频大小 | 100 字节 | 低于视为无语音 |
| 讯飞 API 要求 | 16kHz / 16bit / mono / PCM | 引擎自动标准化任意 WAV |
| 讯飞 API 单次最大 | 10 MB（PCM） | 标准化后超限会拒绝 |
| WebSocket 超时 | 15 秒（连接）+ 15 秒（响应） | 超时后降级 Mock |

## 6. 测试

### 单元测试

```bash
cd ai-service
pytest tests/test_asr.py -v
```

覆盖 17 个测试用例：健康检查、文档约定路径、正常转写、格式校验、大小/时长限制、Mock 引擎确定性等。测试固定使用 Mock 引擎（`ASR_FORCE_MOCK=true`）。

### 真实引擎测试

```bash
# 往返测试（TTS 合成 → ASR 转写 → 文本对比，需 pyttsx3 + espeak-ng）
python scripts/test_asr_real.py --mode roundtrip

# 上传已有 WAV 文件
python scripts/test_asr_real.py --mode file --audio ./test_code/output.wav

# 输出手动测试 curl 命令
python scripts/test_asr_real.py --mode manual
```

## 7. 配置

在 `ai-service/.env` 中配置讯飞 API 凭证：

```bash
# 讯飞语音听写 IAT API
IFLYTEK_APP_ID=your_app_id
IFLYTEK_API_KEY=your_api_key
IFLYTEK_API_SECRET=your_api_secret

# 可选：强制使用 Mock 引擎（跳过讯飞）
# ASR_FORCE_MOCK=true
```

## 8. 技术要点

- **WAV 时长估算**：优先解析 WAV 头中的 `byte_rate` 字段计算真实时长，避免因硬编码 16kHz 假设导致误判（如 44.1kHz 音频被错误估算为 74 秒）。
- **音频标准化**：引擎自动将任意采样率/声道/位深的 WAV 转为讯飞要求的 16kHz 16bit mono PCM，无需调用方预处理。
- **线性插值重采样**：纯 Python 实现，无外部依赖（如 scipy/librosa），适合语音 ASR 场景。
- **Mock 引擎确定性**：基于音频字节采样的哈希值选词，同一音频永远返回相同转写结果，便于测试断言。
