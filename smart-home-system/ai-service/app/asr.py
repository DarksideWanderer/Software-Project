import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlencode, urlunparse

from .config import settings
from .schemas import AsrRequest, AsrResponse


IFLYTEK_HOST = "iat-api.xfyun.cn"
IFLYTEK_PATH = "/v2/iat"
IFLYTEK_WS_SCHEME = "wss"


def transcribe_audio(request: AsrRequest) -> AsrResponse:
    """Transcribe audio with mock fallback or iFlytek WebAPI."""
    if request.mock_text:
        return AsrResponse(
            success=True,
            text=request.mock_text,
            confidence=1.0,
            provider="mock",
            message="ASR mock_text returned.",
        )

    if not request.audio_base64:
        return AsrResponse(
            success=False,
            text="",
            confidence=0.0,
            provider="iflytek",
            message="No audio_base64 provided. Use mock_text for local mock testing.",
        )

    if not _iflytek_configured():
        return AsrResponse(
            success=False,
            text="",
            confidence=0.0,
            provider="iflytek",
            message=(
                "iFlytek ASR is not configured. Set IFLYTEK_APP_ID, "
                "IFLYTEK_API_KEY, and IFLYTEK_API_SECRET, or use mock_text."
            ),
        )

    try:
        text = _transcribe_with_iflytek(request)
    except Exception as exc:  # pragma: no cover - depends on external provider/network
        return AsrResponse(
            success=False,
            text="",
            confidence=0.0,
            provider="iflytek",
            message=f"iFlytek ASR request failed: {exc}",
        )

    return AsrResponse(
        success=bool(text),
        text=text,
        confidence=0.9 if text else 0.0,
        provider="iflytek",
        message="iFlytek ASR completed." if text else "iFlytek ASR returned empty text.",
    )


def _iflytek_configured() -> bool:
    return bool(
        settings.iflytek_app_id
        and settings.iflytek_api_key
        and settings.iflytek_api_secret
    )


def _transcribe_with_iflytek(request: AsrRequest) -> str:
    import websocket

    ws = websocket.create_connection(_build_iflytek_url(), timeout=10)
    try:
        audio_base64, audio_encoding = _prepare_audio_payload(request)
        ws.send(
            json.dumps(
                {
                    "common": {"app_id": settings.iflytek_app_id},
                    "business": {
                        "language": "zh_cn",
                        "domain": "iat",
                        "accent": "mandarin",
                        "vad_eos": 10000,
                    },
                    "data": {
                        "status": 2,
                        "format": f"audio/L16;rate={request.sample_rate}",
                        "audio": audio_base64,
                        "encoding": audio_encoding,
                    },
                },
                ensure_ascii=False,
            )
        )

        pieces: list[str] = []
        while True:
            payload = json.loads(ws.recv())
            if payload.get("code") != 0:
                raise RuntimeError(payload.get("message", "unknown iFlytek ASR error"))

            result = payload.get("data", {}).get("result", {})
            pieces.append(_extract_iflytek_text(result))

            if payload.get("data", {}).get("status") == 2:
                break

        return "".join(pieces)
    finally:
        ws.close()


def _build_iflytek_url() -> str:
    date = format_datetime(datetime.now(timezone.utc), usegmt=True)
    signature_origin = f"host: {IFLYTEK_HOST}\ndate: {date}\nGET {IFLYTEK_PATH} HTTP/1.1"
    signature = hmac.new(
        settings.iflytek_api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature_base64 = base64.b64encode(signature).decode("utf-8")
    authorization_origin = (
        f'api_key="{settings.iflytek_api_key}", '
        'algorithm="hmac-sha256", '
        'headers="host date request-line", '
        f'signature="{signature_base64}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
    query = urlencode(
        {
            "authorization": authorization,
            "date": date,
            "host": IFLYTEK_HOST,
        }
    )
    return urlunparse((IFLYTEK_WS_SCHEME, IFLYTEK_HOST, IFLYTEK_PATH, "", query, ""))


def _prepare_audio_payload(request: AsrRequest) -> tuple[str, str]:
    audio_format = request.format.lower()
    if audio_format == "wav":
        return _strip_wav_header(request.audio_base64), "raw"
    if audio_format == "mp3":
        return request.audio_base64, "lame"
    return request.audio_base64, "raw"


def _strip_wav_header(audio_base64: str) -> str:
    audio = base64.b64decode(audio_base64)
    if not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
        return audio_base64

    offset = 12
    while offset + 8 <= len(audio):
        chunk_id = audio[offset : offset + 4]
        chunk_size = int.from_bytes(audio[offset + 4 : offset + 8], "little")
        data_start = offset + 8
        data_end = data_start + chunk_size
        if chunk_id == b"data":
            return base64.b64encode(audio[data_start:data_end]).decode("utf-8")
        offset = data_end + (chunk_size % 2)
    return audio_base64


def _extract_iflytek_text(result: dict) -> str:
    words = result.get("ws", [])
    text_parts: list[str] = []
    for word in words:
        candidates = word.get("cw", [])
        if candidates:
            text_parts.append(candidates[0].get("w", ""))
    return "".join(text_parts)
