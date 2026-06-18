"""语音识别 (ASR) 模块

实现 FRONTEND_API_REQUIREMENTS.md §8.1 定义的 ASR 转写内部接口。

当前版本使用模拟引擎（mock），可替换为 Whisper / FunASR。
"""

from .routes import router
