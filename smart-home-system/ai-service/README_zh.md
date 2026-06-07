# AI 服务

本目录实现智能家居语音交互助手系统的 AI 子系统。当前 MVP 版本提供：

- `POST /ai/nlu`：规则版文本语义解析，输出稳定结构化 JSON。
- `POST /ai/asr`：语音识别 mock 接口，后续可替换为科大讯飞语音识别 API。
- `GET /health`：服务健康检查和能力说明。

AI 服务只负责解析用户自然语言，不直接控制家电。后端根据 AI 返回的 JSON 统一调度设备、天气、提醒等业务。

## 目录结构

```text
ai-service/
├── app/
│   ├── main.py       # FastAPI 入口
│   ├── schemas.py    # 请求和响应模型
│   ├── nlu.py        # 规则语义解析
│   ├── asr.py        # ASR mock 层
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
