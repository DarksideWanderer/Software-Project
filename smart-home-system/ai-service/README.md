# AI Service Layer

## Introduction
Handles Speech-to-Text (ASR), Natural Language Understanding (NLU), and Text-to-Speech (TTS) pipelines.

## Tech Stack
- **Language**: Python 3.10+
- **Models**: Whisper (ASR), Qwen/Llama (NLU), FunASR (TTS)
- **Frameworks**: PyTorch / ONNX Runtime
- **Protocol**: gRPC / FastAPI (for internal communication)

## Directory Structure
- `models/`: Model weights and artifacts
- `src/asr/`: Speech recognition logic
- `src/nlu/`: Intent parsing and LLM orchestration
- `src/tts/`: Voice synthesis
- `tests/`: AI pipeline validation

---
[中文版文档入口](./README_zh.md)
