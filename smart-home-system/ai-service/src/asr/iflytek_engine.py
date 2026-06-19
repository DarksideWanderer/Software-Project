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
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
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


def _convert_to_pcm(audio_bytes: bytes) -> bytes:
    """将音频数据转为 16kHz 16bit mono PCM。

    当前为简化实现：如果输入已经是 WAV，提取 PCM 数据；
    否则假定为原始 16kHz PCM 或直接透传。
    """
    # 检测 WAV 头（RIFF）
    if audio_bytes[:4] == b"RIFF" and len(audio_bytes) > 44:
        # 跳过 44 字节 WAV 头，提取 PCM 数据
        return audio_bytes[44:]
    # 否则假定已是原始 PCM
    return audio_bytes


def _wav_to_pcm(audio_bytes: bytes) -> bytes:
    """从 WAV 文件中提取 PCM 数据。"""
    if audio_bytes[:4] == b"RIFF":
        # 查找 data chunk
        data_start = audio_bytes.find(b"data")
        if data_start > 0:
            # data chunk: "data" (4) + size (4) + data
            return audio_bytes[data_start + 8:]
    return audio_bytes


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
                            best = max(word_info["cw"], key=lambda x: x.get("sc", 0))
                            final_text += best.get("w", "")
                            confidence_sum += best.get("sc", 0)
                            confidence_count += 1

                if resp_status == 2:
                    # 最终结果，退出循环
                    break

            except asyncio.TimeoutError:
                raise RuntimeError("讯飞 ASR 响应超时（已发送所有音频帧后 15 秒无最终结果）")

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    confidence = round(confidence_sum / confidence_count, 2) if confidence_count > 0 else 0.5

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
    pcm_data = _wav_to_pcm(audio_bytes)

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
