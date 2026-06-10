"""AI 服务层连通性测试"""

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


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
    resp = await client.post("/ai/tts/synthesize")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "not_implemented"
    assert data["module"] == "tts"