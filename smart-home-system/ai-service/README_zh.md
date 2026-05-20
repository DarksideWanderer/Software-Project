# AI 服务层

## 简介
处理语音转文字 (ASR)、自然语言理解 (NLU) 和语音合成 (TTS) 流水线。

## 技术栈
- **语言**: Python 3.10+
- **模型**: Whisper (ASR), Qwen/Llama (NLU), FunASR (TTS)
- **框架**: PyTorch / ONNX Runtime
- **协议**: gRPC / FastAPI (内部通信)

## 目录结构
- `models/`: 模型权重与资源文件
- `src/asr/`: 语音识别逻辑
- `src/nlu/`: 意图解析与大模型编排
- `src/tts/`: 语音合成
- `tests/`: AI 流水线验证
