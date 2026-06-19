"""TTS 模块单元测试"""

import os
import time
import uuid
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------- pyttsx3 Mock 工具 ----------

def _mock_pyttsx3():
    """Mock pyttsx3 引擎，避免测试环境中依赖实际语音引擎"""
    mock_engine = MagicMock()
    mock_engine.save_to_file = MagicMock()
    mock_engine.runAndWait = MagicMock()
    return mock_engine


@pytest.fixture
def mock_pyttsx3():
    with patch("pyttsx3.init", return_value=_mock_pyttsx3()):
        yield


@pytest.fixture
def mock_pyttsx3_and_audio_dir():
    """Mock pyttsx3 并确保 audio_dir 存在"""
    with patch("pyttsx3.init", return_value=_mock_pyttsx3()):
        yield


# ---------- DashScope Mock 类 ----------

class MockAudio:
    url = "https://example.com/audio.wav"
    id = "audio_test_id"
    expires_at = 1766113409


class MockOutput:
    audio = MockAudio()
    text = None
    finish_reason = "stop"
    choices = None


class MockResponse:
    status_code = 200
    request_id = "test-request-id"
    code = ""
    message = ""
    output = MockOutput()
    usage = {}


# ---------- 测试用例 ----------

@pytest.mark.asyncio
async def test_tts_health(client: AsyncClient):
    """测试 TTS 健康检查端点"""
    resp = await client.get("/ai/tts/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "module": "tts"}


@pytest.mark.asyncio
async def test_synthesize_success(client: AsyncClient):
    """测试云端语音合成成功"""
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test-key"}, clear=False):
        with patch(
            "dashscope.audio.qwen_tts.SpeechSynthesizer.call",
            return_value=MockResponse(),
        ) as mock_call:
            resp = await client.post(
                "/ai/tts/synthesize",
                json={"text": "你好，欢迎使用智能家居系统。"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["audio_url"] == "https://example.com/audio.wav"
    assert data["request_id"] == "test-request-id"

    mock_call.assert_called_once_with(
        model="qwen-tts",
        api_key="sk-test-key",
        text="你好，欢迎使用智能家居系统。",
        voice="Cherry",
    )


@pytest.mark.asyncio
async def test_synthesize_with_custom_voice(client: AsyncClient):
    """测试自定义音色"""
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test-key"}, clear=False):
        with patch(
            "dashscope.audio.qwen_tts.SpeechSynthesizer.call",
            return_value=MockResponse(),
        ) as mock_call:
            resp = await client.post(
                "/ai/tts/synthesize",
                json={"text": "测试文本", "voice": "Luna"},
            )

    assert resp.status_code == 200
    mock_call.assert_called_once_with(
        model="qwen-tts",
        api_key="sk-test-key",
        text="测试文本",
        voice="Luna",
    )


@pytest.mark.asyncio
async def test_synthesize_missing_api_key(client: AsyncClient, mock_pyttsx3):
    """测试未配置 API Key → 降级到本地 pyttsx3 合成"""
    with patch.dict(os.environ, {}, clear=True):
        resp = await client.post(
            "/ai/tts/synthesize",
            json={"text": "测试文本"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    # 本地合成返回的是本地音频路径
    assert data["audio_url"].startswith("/ai/tts/audio/")
    assert data["request_id"] is None


@pytest.mark.asyncio
async def test_synthesize_api_error(client: AsyncClient, mock_pyttsx3):
    """测试 dashscope API 返回错误 → 降级到本地合成"""
    error_response = MockResponse()
    error_response.status_code = 400
    error_response.code = "InvalidParameter"
    error_response.message = "参数错误"

    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test-key"}, clear=False):
        with patch(
            "dashscope.audio.qwen_tts.SpeechSynthesizer.call",
            return_value=error_response,
        ):
            resp = await client.post(
                "/ai/tts/synthesize",
                json={"text": "测试文本"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["audio_url"].startswith("/ai/tts/audio/")


@pytest.mark.asyncio
async def test_synthesize_exception(client: AsyncClient, mock_pyttsx3):
    """测试 dashscope 调用异常 → 降级到本地合成"""
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test-key"}, clear=False):
        with patch(
            "dashscope.audio.qwen_tts.SpeechSynthesizer.call",
            side_effect=Exception("网络连接失败"),
        ):
            resp = await client.post(
                "/ai/tts/synthesize",
                json={"text": "测试文本"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["audio_url"].startswith("/ai/tts/audio/")


@pytest.mark.asyncio
async def test_synthesize_missing_text(client: AsyncClient):
    """测试缺少必填字段 text"""
    resp = await client.post(
        "/ai/tts/synthesize",
        json={},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_synthesize_no_audio_url(client: AsyncClient, mock_pyttsx3):
    """测试合成成功但无音频 URL → 降级到本地合成"""
    class _MockAudioNone:
        url = None
        id = None
        expires_at = None

    class _MockOutputNone:
        audio = _MockAudioNone()
        text = None
        finish_reason = "stop"
        choices = None

    class _MockResponseNoAudio:
        status_code = 200
        request_id = "test-no-audio"
        code = ""
        message = ""
        output = _MockOutputNone()
        usage = {}

    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test-key"}, clear=False):
        with patch(
            "dashscope.audio.qwen_tts.SpeechSynthesizer.call",
            return_value=_MockResponseNoAudio(),
        ):
            resp = await client.post(
                "/ai/tts/synthesize",
                json={"text": "测试文本"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["audio_url"].startswith("/ai/tts/audio/")


@pytest.mark.asyncio
async def test_synthesize_fallback_all_fail(client: AsyncClient):
    """测试云端和本地均失败 → 返回 500"""
    with patch.dict(os.environ, {}, clear=True):
        # pyttsx3 也失败
        with patch("pyttsx3.init", side_effect=Exception("pyttsx3 init failed")):
            resp = await client.post(
                "/ai/tts/synthesize",
                json={"text": "测试文本"},
            )

    assert resp.status_code == 500
    assert "均不可用" in resp.json()["detail"]


# ---------- 过期音频清理测试 ----------

def test_cleanup_expired_audio(tmp_path, monkeypatch):
    """测试 _cleanup_expired_audio 删除过期文件"""
    from src.tts.routes import _cleanup_expired_audio, AUDIO_DIR as _REAL_DIR

    # 改用临时目录
    monkeypatch.setattr("src.tts.routes.AUDIO_DIR", str(tmp_path))

    # 创建两个文件：一个过期，一个未过期
    old_file = tmp_path / "old.wav"
    old_file.write_text("dummy")
    now = time.time()
    os.utime(old_file, (now - 2000, now - 2000))  # 约 33 分钟前 → 过期

    fresh_file = tmp_path / "fresh.wav"
    fresh_file.write_text("dummy")
    os.utime(fresh_file, (now - 60, now - 60))  # 1 分钟前 → 未过期

    non_wav = tmp_path / "not_audio.txt"
    non_wav.write_text("should be ignored")

    count = _cleanup_expired_audio()
    assert count == 1  # 只删除了 old.wav
    assert not old_file.exists()  # 已删除
    assert fresh_file.exists()   # 保留
    assert non_wav.exists()      # 保留


def test_cleanup_expired_audio_empty_dir(tmp_path, monkeypatch):
    """测试空目录清理"""
    from src.tts.routes import _cleanup_expired_audio

    monkeypatch.setattr("src.tts.routes.AUDIO_DIR", str(tmp_path))
    count = _cleanup_expired_audio()
    assert count == 0


def test_cleanup_expired_audio_no_dir(monkeypatch):
    """测试目录不存在时静默处理"""
    from src.tts.routes import _cleanup_expired_audio

    monkeypatch.setattr("src.tts.routes.AUDIO_DIR", "/nonexistent/path")
    count = _cleanup_expired_audio()
    assert count == 0
