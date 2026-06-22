"""ASR 子路由 — 语音识别模块

实现 FRONTEND_API_REQUIREMENTS.md §8.1 定义的 ASR 转写内部接口。

采用双引擎降级策略：
1. 云端引擎 — 讯飞语音听写 IAT API
2. 本地降级 — Mock 引擎（确定性，用于测试）
"""

import logging
import os
import time
import uuid
from typing import Optional, Union

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import JSONResponse

from . import iflytek_engine

logger = logging.getLogger(__name__)

# ── 常量 ────────────────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_DURATION_SECONDS = 30
# 仅严格匹配列表中列出的 MIME 类型；不允许通过 audio/* 通配
SUPPORTED_MIME_TYPES = frozenset(
    {
        "audio/webm",
        "audio/webm;codecs=opus",
        "audio/ogg",
        "audio/ogg;codecs=opus",
        "audio/wav",
        "audio/wave",
        "audio/x-wav",
    }
)

# ── 模拟转写结果（Mock 引擎用）──────────────────────────────────────────
_MOCK_TRANSCRIPTS = [
    "打开客厅灯",
    "把空调调到 26 度",
    "关闭电视",
    "把卧室氛围灯调到百分之五十",
    "打开所有灯",
    "设置观影模式",
    "风扇调到三档",
    "冰箱温度调到零下十八度",
    "客厅灯亮度调到百分之八十",
    "开启睡眠模式",
]

router = APIRouter()


# ── 错误响应构建器 ───────────────────────────────────────────────────────


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: Optional[dict] = None,
    request_id: Optional[str] = None,
) -> JSONResponse:
    """构建符合 FRONTEND_API_REQUIREMENTS.md §3.3 统一错误格式的响应。

    错误体包含 request_id，便于跨服务排查（§12.7）。
    """
    error_body: dict = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        error_body["error"]["details"] = details
    if request_id:
        error_body["error"]["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=error_body)


# ── 辅助函数 ─────────────────────────────────────────────────────────────


def _parse_wav_header(data: bytes) -> dict:
    """解析 WAV 文件头，提取音频格式参数。

    Returns:
        dict 包含 sample_rate, bits_per_sample, channels, data_size, duration_seconds,
        或空 dict（非 WAV 或解析失败）。
    """
    try:
        import struct

        if len(data) < 44 or data[:4] != b"RIFF":
            return {}

        # fmt  chunk 偏移（通常紧跟 "WAVE"fmt "）
        if data[8:12] != b"WAVE":
            return {}
        if data[12:16] != b"fmt ":
            return {}

        # 读取 fmt 子块
        fmt_size = struct.unpack_from("<I", data, 16)[0]
        if fmt_size < 16 or len(data) < 20 + fmt_size:
            return {}

        audio_format = struct.unpack_from("<H", data, 20)[0]
        if audio_format != 1:  # 仅支持 PCM
            return {}  # 回退到粗略估算

        channels = struct.unpack_from("<H", data, 22)[0]
        sample_rate = struct.unpack_from("<I", data, 24)[0]
        byte_rate = struct.unpack_from("<I", data, 28)[0]
        block_align = struct.unpack_from("<H", data, 32)[0]
        bits_per_sample = struct.unpack_from("<H", data, 34)[0]

        # 查找 data chunk
        data_offset = data.find(b"data", 36)
        if data_offset < 0:
            return {}
        data_size = struct.unpack_from("<I", data, data_offset + 4)[0]
        # 如果 data_size 为 0 或明显不合理，用文件剩余部分估算
        actual_data_size = min(data_size, len(data) - data_offset - 8) if data_size > 0 else len(data) - data_offset - 8

        if byte_rate > 0:
            duration_seconds = actual_data_size / byte_rate
        else:
            bytes_per_second = sample_rate * channels * (bits_per_sample // 8)
            duration_seconds = actual_data_size / bytes_per_second if bytes_per_second > 0 else 0.0

        return {
            "sample_rate": sample_rate,
            "bits_per_sample": bits_per_sample,
            "channels": channels,
            "data_size": actual_data_size,
            "duration_seconds": duration_seconds,
        }
    except Exception:
        return {}


def _estimate_duration_seconds(data: bytes) -> float:
    """估算音频时长（秒），优先从 WAV 头解析，否则按 16kHz mono 16bit 粗略估算。"""
    wav_info = _parse_wav_header(data)
    if wav_info:
        return wav_info["duration_seconds"]

    # 非 WAV 格式回退到粗略估算（16kHz, 16bit, mono）
    return len(data) / 32000.0


def _validate_and_read_audio(
    upload: UploadFile, request_id: Optional[str] = None
) -> Union[bytes, JSONResponse]:
    """校验上传音频文件的 MIME 类型、大小与时长，读取全部字节。

    Returns:
        音频文件的原始字节；校验失败时返回 JSONResponse 错误体。

    Error responses:
        415: 不支持的音频格式。
        413: 文件超过 10 MB。
        422: 文件为空 / 无可检测语音 / 音频过长。
    """
    # 1. 校验 MIME 类型 —— 仅允许白名单中的类型
    content_type = upload.content_type or ""
    if content_type not in SUPPORTED_MIME_TYPES:
        return _error_response(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="UNSUPPORTED_AUDIO_FORMAT",
            message=f"不支持的音频格式: {content_type}",
            details={"supported_formats": sorted(SUPPORTED_MIME_TYPES)},
            request_id=request_id,
        )

    # 2. 读取全部字节
    data = upload.file.read()

    # 3. 校验文件大小（§7.2: 最大 10 MB）
    if len(data) > MAX_FILE_SIZE_BYTES:
        return _error_response(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            code="AUDIO_TOO_LARGE",
            message=f"音频文件过大，最大允许 {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
            details={
                "max_size_bytes": MAX_FILE_SIZE_BYTES,
                "actual_size_bytes": len(data),
            },
            request_id=request_id,
        )

    # 4. 极小文件视为无有效语音（§7.2: SPEECH_NOT_DETECTED）
    if len(data) < 100:
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="SPEECH_NOT_DETECTED",
            message="未检测到有效语音内容",
            details={"file_size_bytes": len(data)},
            request_id=request_id,
        )

    # 5. 校验音频时长（§7.2: 最大 30 秒）
    # 优先从 WAV 头解析真实参数，回退到 16kHz mono 16bit 粗略估算
    estimated_seconds = _estimate_duration_seconds(data)
    if estimated_seconds > MAX_DURATION_SECONDS:
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="AUDIO_TOO_LONG",
            message=f"音频时长过长，最大允许 {MAX_DURATION_SECONDS} 秒",
            details={
                "max_duration_seconds": MAX_DURATION_SECONDS,
                "estimated_duration_seconds": round(estimated_seconds, 1),
            },
            request_id=request_id,
        )

    return data


def _estimate_duration_ms(audio_bytes: bytes) -> int:
    """根据音频字节数估算时长（毫秒），用于 Mock 模式。

    优先解析 WAV 头获取真实参数，否则按 16kHz mono 16bit 粗略估算。
    """
    raw_seconds = _estimate_duration_seconds(audio_bytes)
    return max(100, min(int(raw_seconds * 1000), MAX_DURATION_SECONDS * 1000))


def _mock_transcribe(audio_bytes: bytes) -> dict:
    """Mock ASR 引擎：返回模拟转写结果。

    在真实部署时，替换为 Whisper / FunASR 调用。
    使用时间+数据混合种子避免每次返回相同结果。
    """
    import time as _time
    seed = sum(
        audio_bytes[i]
        for i in range(0, len(audio_bytes), max(1, len(audio_bytes) // 64))
    ) + int(_time.time() * 1000) % 10000
    idx = seed % len(_MOCK_TRANSCRIPTS)
    text = _MOCK_TRANSCRIPTS[idx]

    duration_ms = _estimate_duration_ms(audio_bytes)
    confidence = round(0.85 + (seed % 15) / 100.0, 2)

    return {
        "text": text,
        "language": "zh-CN",
        "confidence": confidence,
        "duration_ms": duration_ms,
    }


# ── 路由端点 ─────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    """ASR 模块健康检查。"""
    engine = "iflytek" if iflytek_engine.engine_available() else "mock"
    return {"status": "ok", "module": "asr", "engine": engine}


@router.post(
    "/transcriptions",
    status_code=status.HTTP_200_OK,
    summary="ASR 语音转写",
    description=(
        "上传音频文件，返回转写文本、语言、置信度和时长。"
        "符合 FRONTEND_API_REQUIREMENTS.md §8.1。"
        "优先使用讯飞 IAT API，不可用时降级到 Mock 引擎。"
    ),
    responses={
        200: {"description": "转写成功"},
        400: {"description": "请求格式错误"},
        413: {"description": "音频文件过大"},
        415: {"description": "不支持的音频格式"},
        422: {"description": "未检测到有效语音"},
        503: {"description": "ASR 引擎不可用"},
    },
)
async def transcribe_audio(
    audio: UploadFile = File(..., description="浏览器录制的音频文件"),
    language: Optional[str] = Form(default="zh-CN", description="音频语言，默认 zh-CN"),
    request_id: Optional[str] = Form(default=None, description="请求追踪 ID"),
):
    """语音识别主端点 — 双引擎降级。

    1. 优先使用讯飞 IAT API 进行真实语音转写
    2. 讯飞不可用或失败时，降级到 Mock 引擎
    """
    if request_id is None:
        request_id = str(uuid.uuid4())

    # 校验并读取音频
    audio_bytes_or_error = _validate_and_read_audio(audio, request_id=request_id)
    if isinstance(audio_bytes_or_error, JSONResponse):
        return audio_bytes_or_error

    start = time.perf_counter()

    # 1. 尝试真实引擎（讯飞 IAT）
    use_real = (
        iflytek_engine.engine_available()
        and not os.environ.get("ASR_FORCE_MOCK")
    )
    if use_real:
        try:
            result = await iflytek_engine.transcribe(audio_bytes_or_error)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.info("ASR 使用讯飞引擎，text=%s", result["text"][:50])
            return {
                **result,
                "request_id": request_id,
                "engine": "iflytek",
                "processing_ms": elapsed_ms,
            }
        except Exception as e:
            logger.warning("讯飞 ASR 转写失败，降级到 Mock: %s", e)

    # 2. 降级到 Mock 引擎
    logger.info("ASR 使用 Mock 引擎")
    result = _mock_transcribe(audio_bytes_or_error)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return {
        **result,
        "request_id": request_id,
        "engine": "mock",
        "processing_ms": elapsed_ms,
    }


# ── 兼容旧端点（后续可废弃）──────────────────────────────────────────────


@router.post(
    "/transcribe",
    status_code=status.HTTP_200_OK,
    summary="[已废弃] 语音识别端点",
    description="兼容旧版端点，请使用 /transcriptions。",
    deprecated=True,
)
async def transcribe_legacy(
    audio: UploadFile = File(..., description="浏览器录制的音频文件"),
):
    """旧版转写端点，转发到新端点逻辑。"""
    rid = str(uuid.uuid4())
    audio_bytes_or_error = _validate_and_read_audio(audio, request_id=rid)
    if isinstance(audio_bytes_or_error, JSONResponse):
        return audio_bytes_or_error

    # 尝试真实引擎
    if iflytek_engine.engine_available():
        try:
            result = await iflytek_engine.transcribe(audio_bytes_or_error)
            return {
                **result,
                "request_id": rid,
                "engine": "iflytek",
                "deprecated": True,
            }
        except Exception:
            pass

    result = _mock_transcribe(audio_bytes_or_error)
    return {
        **result,
        "request_id": rid,
        "engine": "mock",
        "deprecated": True,
    }
