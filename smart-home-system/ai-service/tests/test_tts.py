"""TTS 模块单元测试"""

import os
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_tts_health(client: AsyncClient):
    """测试 TTS 健康检查端点"""
    resp = await client.get("/ai/tts/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "module": "tts"}


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


@pytest.mark.asyncio
async def test_synthesize_success(client: AsyncClient):
    """测试语音合成成功"""
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
async def test_synthesize_missing_api_key(client: AsyncClient):
    """测试未配置 API Key 时的错误处理"""
    with patch.dict(os.environ, {}, clear=True):
        resp = await client.post(
            "/ai/tts/synthesize",
            json={"text": "测试文本"},
        )

    assert resp.status_code == 500
    assert "DASHSCOPE_API_KEY" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_synthesize_api_error(client: AsyncClient):
    """测试 dashscope API 返回错误"""
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

    assert resp.status_code == 502
    assert "InvalidParameter" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_synthesize_exception(client: AsyncClient):
    """测试 dashscope 调用异常"""
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test-key"}, clear=False):
        with patch(
            "dashscope.audio.qwen_tts.SpeechSynthesizer.call",
            side_effect=Exception("网络连接失败"),
        ):
            resp = await client.post(
                "/ai/tts/synthesize",
                json={"text": "测试文本"},
            )

    assert resp.status_code == 502
    assert "网络连接失败" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_synthesize_missing_text(client: AsyncClient):
    """测试缺少必填字段 text"""
    resp = await client.post(
        "/ai/tts/synthesize",
        json={},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_synthesize_no_audio_url(client: AsyncClient):
    """测试合成成功但无音频 URL 的情况"""
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

    assert resp.status_code == 502
    assert "缺少音频数据" in resp.json()["detail"]
