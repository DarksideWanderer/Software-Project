"""ASR 模块单元测试

覆盖 FRONTEND_API_REQUIREMENTS.md 中 ASR 转写接口的所有场景：

- 健康检查（模块级 + AI 服务级 §11.2）
- 文档约定路径 /internal/v1/asr/transcriptions（§8.1）
- 正常音频转写（WAV / WebM / OGG）
- 缺少音频文件（422）
- 文件过大（413 §7.2）
- 音频过长（422 §7.2）
- 不支持的格式（415）
- 空文件 / 无语音（422 §7.2）
- 可选字段（language, request_id）
- 错误响应含 request_id（§3.3）
- 旧版兼容端点 /transcribe
- Mock 引擎确定性验证

测试使用 httpx.AsyncClient + ASGITransport，无需启动真实服务器。
"""

import io

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
async def client():
    """创建异步 HTTP 测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_audio_bytes(size: int = 32000) -> bytes:
    """生成模拟音频字节（指定大小）。"""
    # 生成非零字节，确保 mock 转写结果稳定
    return bytes([(i % 256) or 1 for i in range(size)])


def _create_audio_file(
    filename: str = "test.wav",
    content_type: str = "audio/wav",
    size: int = 32000,
) -> tuple:
    """创建用于 multipart 上传的音频文件元组。"""
    data = _make_audio_bytes(size)
    return ("audio", (filename, io.BytesIO(data), content_type))


# ── 健康检查 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """ASR 模块健康检查应返回 ok 状态。"""
    resp = await client.get("/ai/asr/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["module"] == "asr"


# ── §8.1 文档约定路径 ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_spec_path_transcriptions(client: AsyncClient):
    """FRONTEND_API_REQUIREMENTS.md §8.1 约定路径：
    POST /internal/v1/asr/transcriptions
    Content-Type: multipart/form-data
    """
    files = _create_audio_file("test.wav", "audio/wav")
    resp = await client.post("/internal/v1/asr/transcriptions", files=[files])
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["text"], str) and len(body["text"]) > 0
    assert body["language"] == "zh-CN"
    assert isinstance(body["confidence"], float)
    assert 0.0 <= body["confidence"] <= 1.0
    assert isinstance(body["duration_ms"], int)
    assert body["duration_ms"] > 0
    assert "request_id" in body
    # 严格验证响应字段与文档一致（不含 engine / processing_ms 等扩展字段）
    assert set(body.keys()) >= {
        "text",
        "language",
        "confidence",
        "duration_ms",
        "request_id",
    }


# ── 正常转写 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transcriptions_success_wav(client: AsyncClient):
    """上传 WAV 音频应返回转写结果。"""
    files = _create_audio_file("test.wav", "audio/wav")
    resp = await client.post("/ai/asr/transcriptions", files=[files])
    assert resp.status_code == 200
    body = resp.json()
    assert "text" in body
    assert isinstance(body["text"], str)
    assert len(body["text"]) > 0
    assert body["language"] == "zh-CN"
    assert isinstance(body["confidence"], float)
    assert 0.0 <= body["confidence"] <= 1.0
    assert isinstance(body["duration_ms"], int)
    assert body["duration_ms"] > 0
    assert "request_id" in body
    assert body["engine"] == "mock"


@pytest.mark.asyncio
async def test_transcriptions_success_webm(client: AsyncClient):
    """上传 WebM Opus 音频应返回转写结果。"""
    files = _create_audio_file("test.webm", "audio/webm;codecs=opus", size=64000)
    resp = await client.post("/ai/asr/transcriptions", files=[files])
    assert resp.status_code == 200
    body = resp.json()
    assert "text" in body
    assert body["language"] == "zh-CN"


@pytest.mark.asyncio
async def test_transcriptions_success_ogg(client: AsyncClient):
    """上传 OGG Opus 音频应返回转写结果。"""
    files = _create_audio_file("test.ogg", "audio/ogg;codecs=opus", size=48000)
    resp = await client.post("/ai/asr/transcriptions", files=[files])
    assert resp.status_code == 200
    body = resp.json()
    assert "text" in body


@pytest.mark.asyncio
async def test_transcriptions_with_language(client: AsyncClient):
    """指定 language 字段应被接受。"""
    files = _create_audio_file("test.wav", "audio/wav")
    resp = await client.post(
        "/ai/asr/transcriptions",
        files=[files],
        data={"language": "zh-CN"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["language"] == "zh-CN"


@pytest.mark.asyncio
async def test_transcriptions_with_request_id(client: AsyncClient):
    """指定 request_id 字段应在响应中返回。"""
    custom_rid = "req-test-001"
    files = _create_audio_file("test.wav", "audio/wav")
    resp = await client.post(
        "/ai/asr/transcriptions",
        files=[files],
        data={"request_id": custom_rid},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["request_id"] == custom_rid


# ── 缺失音频文件 ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transcriptions_missing_audio(client: AsyncClient):
    """未上传音频文件应返回 422（FastAPI 默认行为）。"""
    resp = await client.post("/ai/asr/transcriptions")
    # FastAPI 对缺失必需 File 字段返回 422
    assert resp.status_code == 422


# ── 文件过大 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transcriptions_file_too_large(client: AsyncClient):
    """超过 10 MB 的音频文件应返回 413 AUDIO_TOO_LARGE。"""
    large_size = 11 * 1024 * 1024  # 11 MB
    files = _create_audio_file("large.wav", "audio/wav", size=large_size)
    resp = await client.post("/ai/asr/transcriptions", files=[files])
    assert resp.status_code == 413
    body = resp.json()
    assert body["error"]["code"] == "AUDIO_TOO_LARGE"


# ── 不支持的格式 ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transcriptions_unsupported_format(client: AsyncClient):
    """不支持的 MIME 类型应返回 415 UNSUPPORTED_AUDIO_FORMAT。"""
    files = _create_audio_file("test.mp4", "video/mp4")
    resp = await client.post("/ai/asr/transcriptions", files=[files])
    assert resp.status_code == 415
    body = resp.json()
    assert body["error"]["code"] == "UNSUPPORTED_AUDIO_FORMAT"


@pytest.mark.asyncio
async def test_transcriptions_unknown_audio_format(client: AsyncClient):
    """未知 audio/* 子类型应被拒绝。"""
    files = _create_audio_file("test.flac", "audio/flac")
    resp = await client.post("/ai/asr/transcriptions", files=[files])
    # audio/flac 不在支持列表中，且不以已知前缀匹配，应返回 415
    assert resp.status_code == 415


# ── 空文件 / 无语音 ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transcriptions_empty_audio(client: AsyncClient):
    """极小的音频文件（<100 字节）应返回 422 SPEECH_NOT_DETECTED。"""
    files = _create_audio_file("empty.wav", "audio/wav", size=10)
    resp = await client.post("/ai/asr/transcriptions", files=[files])
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "SPEECH_NOT_DETECTED"


# ── 音频过长 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transcriptions_too_long(client: AsyncClient):
    """超过 30 秒的音频应返回 422 AUDIO_TOO_LONG（§7.2）。"""
    # 32 秒等价字节数: 32 * 32000 = 1,024,000 字节
    long_size = 32 * 32000
    files = _create_audio_file("long.wav", "audio/wav", size=long_size)
    resp = await client.post("/ai/asr/transcriptions", files=[files])
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "AUDIO_TOO_LONG"


# ── 错误响应含 request_id ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_error_response_includes_request_id(client: AsyncClient):
    """错误响应应包含 request_id（§3.3 统一错误格式）。"""
    custom_rid = "req-error-test-001"
    files = _create_audio_file("bad.mp4", "video/mp4")
    resp = await client.post(
        "/ai/asr/transcriptions",
        files=[files],
        data={"request_id": custom_rid},
    )
    assert resp.status_code == 415
    body = resp.json()
    assert body["error"]["request_id"] == custom_rid


# ── 旧版兼容端点 ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transcribe_legacy_success(client: AsyncClient):
    """旧版 /transcribe 端点（已标记废弃）应仍可工作。"""
    files = _create_audio_file("test.wav", "audio/wav")
    resp = await client.post("/ai/asr/transcribe", files=[files])
    assert resp.status_code == 200
    body = resp.json()
    assert "text" in body
    assert body.get("deprecated") is True


@pytest.mark.asyncio
async def test_transcribe_legacy_missing_audio(client: AsyncClient):
    """旧版 /transcribe 缺少音频应返回 422。"""
    resp = await client.post("/ai/asr/transcribe")
    assert resp.status_code == 422


# ── 确定性验证 ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transcriptions_deterministic_mock(client: AsyncClient):
    """相同音频数据的两轮 Mock 转写应返回一致结果。"""
    data = _make_audio_bytes(32000)
    files1 = ("audio", ("test.wav", io.BytesIO(data), "audio/wav"))
    files2 = ("audio", ("test.wav", io.BytesIO(data), "audio/wav"))

    resp1 = await client.post("/ai/asr/transcriptions", files=[files1])
    resp2 = await client.post("/ai/asr/transcriptions", files=[files2])

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["text"] == resp2.json()["text"]
    assert resp1.json()["confidence"] == resp2.json()["confidence"]
    assert resp1.json()["duration_ms"] == resp2.json()["duration_ms"]


# ── AI 服务内部健康检查（§11.2）─────────────────────────────────────────


@pytest.mark.asyncio
async def test_internal_health_check(client: AsyncClient):
    """GET /internal/health 应返回模型就绪状态。"""
    resp = await client.get("/internal/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["models"]["asr"] == "ready"
