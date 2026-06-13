"""AI 服务层连通性测试"""

import os
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


class _MockAudio:
    url = "https://example.com/audio.wav"
    id = "audio_test_id"
    expires_at = 1766113409


class _MockOutput:
    audio = _MockAudio()
    text = None
    finish_reason = "stop"
    choices = None


class _MockDashScopeResponse:
    status_code = 200
    request_id = "test-request-id"
    code = ""
    message = ""
    output = _MockOutput()
    usage = {}


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """测试全局健康检查"""
    resp = await client.get("/ai/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "ai-service"}


@pytest.mark.asyncio
async def test_asr_health(client: AsyncClient):
    """测试 ASR 模块健康检查"""
    resp = await client.get("/ai/asr/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "module": "asr"}


@pytest.mark.asyncio
async def test_asr_transcribe(client: AsyncClient):
    """测试 ASR 转写端点"""
    resp = await client.post("/ai/asr/transcribe")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "not_implemented"
    assert data["module"] == "asr"


@pytest.mark.asyncio
async def test_nlu_health(client: AsyncClient):
    """测试 NLU 模块健康检查"""
    resp = await client.get("/ai/nlu/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "module": "nlu"}


@pytest.mark.asyncio
async def test_nlu_parse(client: AsyncClient):
    """测试 NLU 解析端点"""
    resp = await client.post("/ai/nlu/parse")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "not_implemented"
    assert data["module"] == "nlu"


@pytest.mark.asyncio
async def test_tts_health(client: AsyncClient):
    """测试 TTS 模块健康检查"""
    resp = await client.get("/ai/tts/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "module": "tts"}


@pytest.mark.asyncio
async def test_tts_synthesize(client: AsyncClient):
    """测试 TTS 合成端点"""
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test-key"}, clear=False):
        with patch(
            "dashscope.audio.qwen_tts.SpeechSynthesizer.call",
            return_value=_MockDashScopeResponse(),
        ):
            resp = await client.post(
                "/ai/tts/synthesize",
                json={"text": "你好，欢迎使用智能家居系统。"},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["audio_url"] == "https://example.com/audio.wav"