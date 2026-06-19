"""讯飞语音听写 (iFlytek IAT) ASR 引擎

基于讯飞 WebSocket API 实现真实语音转写。
文档: https://www.xfyun.cn/doc/asr/voicedictation/API.html

依赖: websockets>=12.0
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import struct
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from urllib.parse import urlencode

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# ── 讯飞 API 配置 ────────────────────────────────────────────────────────
IFLYTEK_APP_ID = os.environ.get("IFLYTEK_APP_ID", "")
IFLYTEK_API_KEY = os.environ.get("IFLYTEK_API_KEY", "")
IFLYTEK_API_SECRET = os.environ.get("IFLYTEK_API_SECRET", "")

IAT_HOST_URL = "wss://iat-api.xfyun.cn/v2/iat"
AUDIO_SAMPLE_RATE = 16000  # 16kHz
AUDIO_FRAME_SIZE = 1280    # 每帧 1280 字节（80ms @ 16kHz 16bit mono）
MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


# ── 鉴权 ────────────────────────────────────────────────────────────────

def _build_auth_url() -> str:
    """构建带鉴权签名的 WebSocket URL。"""
    host = "iat-api.xfyun.cn"
    path = "/v2/iat"
    now = datetime.now(timezone.utc)
    date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # 签名原始字符串
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    signature_sha = hmac.new(
        IFLYTEK_API_SECRET.encode(),
        signature_origin.encode(),
        hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode()

    # 构建 authorization
    authorization_origin = (
        f'api_key="{IFLYTEK_API_KEY}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode()).decode()

    # 构建 URL
    params = {
        "authorization": authorization,
        "date": date,
        "host": host,
    }
    return f"{IAT_HOST_URL}?{urlencode(params)}"


# ── 音频格式转换 ────────────────────────────────────────────────────────


def _parse_wav_info(audio_bytes: bytes) -> Optional[dict]:
    """解析 WAV 文件头，提取格式信息与原始 PCM 数据。

    Returns:
        dict(sample_rate, channels, bits_per_sample, pcm_data) 或 None。
    """
    try:
        if len(audio_bytes) < 44 or audio_bytes[:4] != b"RIFF":
            return None
        if audio_bytes[8:12] != b"WAVE":
            return None

        # 定位 fmt  chunk
        fmt_offset = 12
        while fmt_offset + 8 <= len(audio_bytes):
            chunk_id = audio_bytes[fmt_offset:fmt_offset + 4]
            chunk_size = struct.unpack_from("<I", audio_bytes, fmt_offset + 4)[0]
            if chunk_id == b"fmt ":
                if chunk_size < 16 or fmt_offset + 8 + chunk_size > len(audio_bytes):
                    return None
                audio_format = struct.unpack_from("<H", audio_bytes, fmt_offset + 8)[0]
                if audio_format != 1:  # 非 PCM（如压缩格式），暂不支持
                    return None
                channels = struct.unpack_from("<H", audio_bytes, fmt_offset + 10)[0]
                sample_rate = struct.unpack_from("<I", audio_bytes, fmt_offset + 12)[0]
                bits_per_sample = struct.unpack_from("<H", audio_bytes, fmt_offset + 22)[0]
                break
            fmt_offset += 8 + chunk_size
        else:
            return None

        # 定位 data chunk
        data_offset = fmt_offset
        while data_offset + 8 <= len(audio_bytes):
            chunk_id = audio_bytes[data_offset:data_offset + 4]
            chunk_size = struct.unpack_from("<I", audio_bytes, data_offset + 4)[0]
            if chunk_id == b"data":
                pcm_start = data_offset + 8
                pcm_end = min(pcm_start + chunk_size, len(audio_bytes))
                pcm_data = audio_bytes[pcm_start:pcm_end]
                return {
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "bits_per_sample": bits_per_sample,
                    "pcm_data": pcm_data,
                }
            data_offset += 8 + chunk_size
        return None
    except Exception:
        return None


def _resample_pcm(
    pcm_data: bytes,
    src_rate: int,
    dst_rate: int,
    channels: int,
    bits_per_sample: int,
) -> bytes:
    """纯 Python 线性插值重采样 PCM 音频。

    将任意采样率的 PCM 数据重采样到目标采样率。
    使用线性插值，适合语音 ASR 场景。
    """
    if src_rate == dst_rate:
        return pcm_data

    bytes_per_sample = bits_per_sample // 8
    bytes_per_frame = bytes_per_sample * channels

    # 计算总帧数（一个帧 = 所有声道的一个采样点）
    total_src_frames = len(pcm_data) // bytes_per_frame
    if total_src_frames == 0:
        return b""

    # 目标帧数
    ratio = dst_rate / src_rate
    total_dst_frames = max(1, int(total_src_frames * ratio))

    # 将字节数据转为采样值列表（16-bit signed int）
    sample_count = total_src_frames * channels
    src_samples = struct.unpack_from(f"<{sample_count}h", pcm_data, 0)

    result = bytearray()

    for dst_frame in range(total_dst_frames):
        # 源位置（浮点）
        src_pos = dst_frame / ratio
        src_idx = int(src_pos)
        frac = src_pos - src_idx

        # 为每个声道做线性插值
        for ch in range(channels):
            idx0 = min(src_idx, total_src_frames - 1) * channels + ch
            idx1 = min(src_idx + 1, total_src_frames - 1) * channels + ch

            s0 = src_samples[idx0]
            s1 = src_samples[idx1]

            # 线性插值
            val = int(s0 + (s1 - s0) * frac)
            # 限幅到 16-bit 有符号范围
            val = max(-32768, min(32767, val))
            result.extend(struct.pack("<h", val))

    return bytes(result)


def _convert_stereo_to_mono(pcm_data: bytes, bits_per_sample: int) -> bytes:
    """立体声转单声道：取左右声道平均值。"""
    bytes_per_sample = bits_per_sample // 8
    # 每帧 = L + R，各 bytes_per_sample 字节
    frame_size = bytes_per_sample * 2
    total_frames = len(pcm_data) // frame_size
    if total_frames == 0:
        return pcm_data

    result = bytearray()
    for i in range(total_frames):
        offset = i * frame_size
        l = struct.unpack_from("<h", pcm_data, offset)[0]
        r = struct.unpack_from("<h", pcm_data, offset + bytes_per_sample)[0]
        mono = (l + r) // 2
        result.extend(struct.pack("<h", mono))
    return bytes(result)


def _normalize_audio(audio_bytes: bytes) -> Tuple[bytes, dict]:
    """将任意 WAV 音频标准化为 16kHz 16-bit mono PCM。

    Args:
        audio_bytes: 原始音频字节（WAV 格式或原始 PCM）。

    Returns:
        (normalized_pcm_bytes, info_dict)
        info_dict 包含 original_sample_rate, original_channels 等调试信息。
    """
    info = {
        "original_sample_rate": 16000,
        "original_channels": 1,
        "original_bits": 16,
    }

    wav_info = _parse_wav_info(audio_bytes)
    if wav_info is None:
        # 非 WAV，假定已是 16kHz 16-bit mono PCM
        logger.info("非 WAV 格式，假定为 16kHz 16bit mono PCM (%d bytes)", len(audio_bytes))
        return audio_bytes, info

    src_rate = wav_info["sample_rate"]
    channels = wav_info["channels"]
    bits = wav_info["bits_per_sample"]
    pcm = wav_info["pcm_data"]

    info["original_sample_rate"] = src_rate
    info["original_channels"] = channels
    info["original_bits"] = bits

    logger.info(
        "WAV 解析: %dHz %dch %dbit, PCM=%d bytes, 时长≈%.1fs",
        src_rate, channels, bits, len(pcm),
        len(pcm) / (src_rate * channels * bits // 8) if src_rate > 0 else 0,
    )

    # 1. 重采样到 16kHz
    if src_rate != AUDIO_SAMPLE_RATE:
        logger.info("重采样 %dHz → %dHz", src_rate, AUDIO_SAMPLE_RATE)
        pcm = _resample_pcm(pcm, src_rate, AUDIO_SAMPLE_RATE, channels, bits)

    # 2. 立体声 → 单声道
    if channels > 1:
        logger.info("立体声 → 单声道 (%dch → 1ch)", channels)
        pcm = _convert_stereo_to_mono(pcm, bits)

    # 3. 确保 16-bit（如果源是 8/24/32-bit）
    if bits != 16:
        logger.info("位深转换 %dbit → 16bit", bits)
        # 简单处理：对于 8-bit unsigned，转为 signed 16-bit
        if bits == 8:
            samples = struct.unpack(f"<{len(pcm)}B", pcm)
            pcm = struct.pack(f"<{len(samples)}h", *((s - 128) * 256 for s in samples))
        elif bits == 24:
            # 24-bit → 16-bit：取高 16 位
            frame_count = len(pcm) // 3
            result = bytearray()
            for i in range(frame_count):
                b0, b1, b2 = pcm[i * 3], pcm[i * 3 + 1], pcm[i * 3 + 2]
                # 24-bit signed little-endian
                s24 = b0 | (b1 << 8) | (b2 << 16)
                if s24 & 0x800000:
                    s24 -= 0x1000000
                s16 = s24 >> 8
                s16 = max(-32768, min(32767, s16))
                result.extend(struct.pack("<h", s16))
            pcm = bytes(result)
        elif bits == 32:
            frame_count = len(pcm) // 4
            result = bytearray()
            for i in range(frame_count):
                s32 = struct.unpack_from("<i", pcm, i * 4)[0]
                s16 = s32 >> 16
                s16 = max(-32768, min(32767, s16))
                result.extend(struct.pack("<h", s16))
            pcm = bytes(result)

    logger.info("标准化完成: %d bytes (≈%.1fs @ 16kHz mono 16bit)",
                len(pcm), len(pcm) / 32000.0)
    return pcm, info


# 保留旧接口兼容
def _convert_to_pcm(audio_bytes: bytes) -> bytes:
    """已废弃：使用 _normalize_audio 代替。"""
    return _normalize_audio(audio_bytes)[0]


def _wav_to_pcm(audio_bytes: bytes) -> bytes:
    """已废弃：使用 _normalize_audio 代替。"""
    return _normalize_audio(audio_bytes)[0]


# ── 核心转写逻辑 ────────────────────────────────────────────────────────


async def _transcribe_websocket(audio_pcm: bytes) -> dict:
    """通过 WebSocket 连接讯飞 IAT API 进行语音转写。

    协议要点：
    - 第 1 帧：common + business + data (status=0)
    - 第 2..N 帧：仅 data (status=1)
    - 最后 1 帧：仅 data (status=2)，发完后等待服务端最终结果
    - 服务端在收到 status=2 后才返回最终转写结果
    """
    import websockets

    url = _build_auth_url()
    start_time = time.perf_counter()

    final_text = ""
    confidence_sum = 0.0
    confidence_count = 0

    common_params = {"app_id": IFLYTEK_APP_ID}
    business_params = {
        "language": "zh_cn",
        "domain": "iat",
        "accent": "mandarin",
        "vad_eos": 3000,
    }

    total_frames = max(1, (len(audio_pcm) + AUDIO_FRAME_SIZE - 1) // AUDIO_FRAME_SIZE)
    total_frames += 1  # +1 for the final status=2 frame with empty audio

    async with websockets.connect(url, ping_interval=10, close_timeout=5, open_timeout=15) as ws:
        # ── 发送所有帧 ────────────────────────────────────────────
        for i in range(total_frames):
            is_first = (i == 0)
            is_last = (i == total_frames - 1)

            if is_last:
                # 最后帧：空音频，status=2
                frame_data: dict = {
                    "data": {
                        "status": 2,
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": "",
                    },
                }
            else:
                start_byte = i * AUDIO_FRAME_SIZE
                end_byte = min(start_byte + AUDIO_FRAME_SIZE, len(audio_pcm))
                frame = audio_pcm[start_byte:end_byte]
                status = 0 if is_first else 1

                frame_data = {
                    "data": {
                        "status": status,
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": base64.b64encode(frame).decode(),
                    },
                }

            if is_first:
                frame_data["common"] = common_params
                frame_data["business"] = business_params

            await ws.send(json.dumps(frame_data))

        # ── 收集响应 ──────────────────────────────────────────────
        while True:
            try:
                resp_raw = await asyncio.wait_for(ws.recv(), timeout=15)
                resp = json.loads(resp_raw)

                code = resp.get("code", 0)
                if code != 0:
                    msg = resp.get("message", "unknown error")
                    raise RuntimeError(f"讯飞 ASR 返回错误: code={code} message={msg}")

                data = resp.get("data", {})
                resp_status = data.get("status", 0)

                # 解析结果
                result_str = data.get("result", "{}")
                if isinstance(result_str, str):
                    try:
                        result = json.loads(result_str)
                    except json.JSONDecodeError:
                        result = {}
                else:
                    result = result_str

                if "ws" in result:
                    for word_info in result["ws"]:
                        if "cw" in word_info:
                            # 兼容多种可能的置信度字段名（sc / score / confidence）
                            # 讯飞返回 0-100 整数，归一化到 0-1
                            def _word_score(candidate: dict) -> float:
                                for key in ("sc", "score", "confidence"):
                                    val = candidate.get(key)
                                    if val is not None:
                                        try:
                                            v = float(val)
                                            return v / 100.0 if v > 1 else v
                                        except (ValueError, TypeError):
                                            continue
                                return 0.0

                            best = max(word_info["cw"], key=_word_score)
                            final_text += best.get("w", "")
                            confidence_sum += _word_score(best)
                            confidence_count += 1

                if resp_status == 2:
                    # 最终结果，退出循环
                    break

            except asyncio.TimeoutError:
                raise RuntimeError("讯飞 ASR 响应超时（已发送所有音频帧后 15 秒无最终结果）")

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

    if confidence_count > 0 and confidence_sum == 0.0:
        logger.warning(
            "讯飞 ASR 未返回置信度分数（已识别 %d 个词，但所有 sc/score 字段均为 0 或缺失），"
            "降级使用默认置信度 0.5",
            confidence_count,
        )
        confidence = 0.5
    elif confidence_count > 0:
        confidence = round(confidence_sum / confidence_count, 2)
    else:
        confidence = 0.5

    if not final_text:
        raise RuntimeError("讯飞 ASR 未返回转写结果（可能是静音或无法识别）")

    return {
        "text": final_text,
        "confidence": confidence,
        "duration_ms": elapsed_ms,
    }


async def transcribe(audio_bytes: bytes) -> dict:
    """异步接口：转写音频。

    Args:
        audio_bytes: 原始音频字节（支持 WAV 和原始 PCM）。

    Returns:
        dict: {text, language, confidence, duration_ms, engine}

    Raises:
        RuntimeError: 转写失败。
    """
    pcm_data, wav_info = _normalize_audio(audio_bytes)

    if len(pcm_data) > MAX_AUDIO_SIZE_BYTES:
        raise RuntimeError(f"音频过大: {len(pcm_data)} bytes (max {MAX_AUDIO_SIZE_BYTES})")

    if len(pcm_data) < 100:
        raise RuntimeError("音频过短，未检测到有效语音")

    result = await _transcribe_websocket(pcm_data)

    return {
        "text": result["text"],
        "language": "zh-CN",
        "confidence": result["confidence"],
        "duration_ms": result["duration_ms"],
        "engine": "iflytek",
    }


def engine_available() -> bool:
    """检查讯飞 ASR 引擎是否可用。"""
    return bool(IFLYTEK_APP_ID and IFLYTEK_API_KEY and IFLYTEK_API_SECRET)
