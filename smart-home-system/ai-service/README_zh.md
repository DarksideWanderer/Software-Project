# AI 服务

本目录实现智能家居语音交互助手系统的 AI 子系统。当前 MVP 版本提供：

- `POST /ai/nlu`：规则版文本语义解析，输出稳定结构化 JSON。
- `POST /ai/asr`：语音识别接口，优先支持 `mock_text` 本地模拟；传入真实音频且配置科大讯飞密钥后调用科大讯飞语音听写 WebAPI。
- `GET /health`：服务健康检查和能力说明。

AI 服务只负责解析用户自然语言，不直接控制家电。后端根据 AI 返回的 JSON 统一调度设备、天气、提醒等业务。

## 目录结构

```text
ai-service/
├── app/
│   ├── main.py       # FastAPI 入口
│   ├── schemas.py    # 请求和响应模型
│   ├── nlu.py        # 规则语义解析
│   ├── asr.py        # ASR mock 与科大讯飞 WebAPI 接入
│   └── config.py     # 外部服务配置占位
├── tests/
│   └── test_nlu.py   # NLU 测试集
└── requirements.txt
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8100
```

Swagger 文档地址：

```text
http://localhost:8100/docs
```

## NLU 接口示例

请求：

```json
{
  "text": "打开客厅灯",
  "context": {
    "user_id": "demo-user",
    "last_device_type": null,
    "last_location": null
  }
}
```

响应：

```json
{
  "success": true,
  "intent": "device_control",
  "confidence": 0.9,
  "slots": {
    "device_type": "light",
    "location": "living_room",
    "action": "turn_on",
    "value": null,
    "unit": null,
    "city": null,
    "datetime": null,
    "content": null
  },
  "need_clarification": false,
  "reply": "好的，已识别为打开客厅灯。"
}
```

## ASR Mock 接口示例

请求：

```json
{
  "audio_base64": "",
  "format": "wav",
  "sample_rate": 16000,
  "mock_text": "打开客厅灯"
}
```

响应：

```json
{
  "success": true,
  "text": "打开客厅灯",
  "confidence": 1.0,
  "provider": "mock",
  "message": "ASR mock_text returned."
}
```

## 科大讯飞 ASR 接入

当前 `/ai/asr` 保留 mock 兜底，同时已经预留真实科大讯飞语音听写 WebAPI 调用逻辑。

### 配置环境变量

推荐在 `ai-service` 目录下新建 `.env` 文件：

```env
IFLYTEK_APP_ID=你的APPID
IFLYTEK_API_KEY=你的APIKey
IFLYTEK_API_SECRET=你的APISecret
DEEPSEEK_API_KEY=你的DeepSeek API Key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_API_KEY=
```

项目提供了 `.env.example` 作为字段示例。`.env` 中会包含真实密钥，不要提交到 Git；`.env.example` 只包含占位符，可以提交给团队成员参考。

也可以在 PowerShell 中临时配置：


```powershell
$env:IFLYTEK_APP_ID="你的APPID"
$env:IFLYTEK_API_KEY="你的APIKey"
$env:IFLYTEK_API_SECRET="你的APISecret"
```

配置后重启 AI 服务，并访问：

```text
http://localhost:8100/health
```

如果配置成功，响应中的 `external_providers_configured.iflytek` 应为 `true`。

### 真实 ASR 请求示例

请求：

```json
{
  "audio_base64": "这里填写16k单声道音频的base64",
  "format": "wav",
  "sample_rate": 16000,
  "mock_text": null
}
```

说明：

1. `mock_text` 有值时始终走 mock，不会调用科大讯飞。
2. `mock_text` 为空且 `audio_base64` 有值时，服务会尝试调用科大讯飞。
3. `format=wav` 时服务会自动去掉 WAV 文件头，只把 PCM 数据发送给科大讯飞。
4. 当前建议使用 16k、16bit、单声道音频。

## DeepSeek V4 NLU 接入

`/ai/nlu` 当前采用“规则优先、DeepSeek 兜底”的混合解析方式：

1. 常见课程演示指令优先走本地规则解析，例如“打开客厅灯”。
2. 本地规则无法理解或置信度较低时，如果已配置 DeepSeek，则调用 DeepSeek V4。
3. DeepSeek 只返回结构化 JSON，不直接控制设备、不访问数据库、不调用 C++ 模拟器。
4. 如果 DeepSeek 调用失败，系统会自动回退到规则解析结果，保证课程演示稳定。

### DeepSeek 配置

在 `.env` 中加入：

```env
DEEPSEEK_API_KEY=你的DeepSeek API Key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

说明：

1. 默认模型为 `deepseek-v4-flash`，适合课程项目联调。
2. 如果需要更高质量解析，可以把 `DEEPSEEK_MODEL` 改为 `deepseek-v4-pro`。
3. 如果未配置 `DEEPSEEK_API_KEY`，服务会尝试兼容读取 `LLM_API_KEY`。
4. 修改 `.env` 后需要重启服务。

### DeepSeek NLU 测试样例

规则版可直接处理：

```json
{
  "text": "打开客厅灯",
  "context": null
}
```

更适合 DeepSeek 兜底处理：

```json
{
  "text": "我有点冷，把卧室弄暖和一点",
  "context": null
}
```

期望返回仍然是统一的 NLU 结构，例如：

```json
{
  "success": true,
  "intent": "device_control",
  "confidence": 0.86,
  "slots": {
    "device_type": "air_conditioner",
    "location": "bedroom",
    "action": "increase_temperature",
    "value": null,
    "unit": "celsius",
    "city": null,
    "datetime": null,
    "content": null
  },
  "need_clarification": false,
  "reply": "好的，已识别为调高卧室空调温度。"
}
```

## 支持的 intent

- `device_control`
- `device_query`
- `weather_query`
- `reminder_create`
- `scene_mode`
- `unknown`

## 支持的 action

- `turn_on`
- `turn_off`
- `set_temperature`
- `increase_temperature`
- `decrease_temperature`
- `set_brightness`
- `increase_brightness`
- `decrease_brightness`
- `open`
- `close`
- `set_open_percent`
- `query_status`

## 运行测试

```bash
pytest
```
