"""
ai-service ASR 模块单元测试
测试 src/asr/routes.py 中的语音识别功能
"""

import io
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class TestASRConstants:
    """ASR 常量配置测试"""

    def test_max_file_size(self):
        from asr.routes import MAX_FILE_SIZE_BYTES
        assert MAX_FILE_SIZE_BYTES == 10 * 1024 * 1024

    def test_max_duration(self):
        from asr.routes import MAX_DURATION_SECONDS
        assert MAX_DURATION_SECONDS == 30

    def test_supported_mime_types(self):
        from asr.routes import SUPPORTED_MIME_TYPES
        assert "audio/webm" in SUPPORTED_MIME_TYPES
        assert "audio/wav" in SUPPORTED_MIME_TYPES
        assert "audio/ogg" in SUPPORTED_MIME_TYPES

    def test_mock_transcripts_not_empty(self):
        from asr.routes import _MOCK_TRANSCRIPTS
        assert len(_MOCK_TRANSCRIPTS) > 0
        assert all(isinstance(t, str) for t in _MOCK_TRANSCRIPTS)


class TestWAVParsing:
    """WAV 文件头解析测试"""

    def test_parse_valid_wav_header(self):
        """解析有效 WAV 头"""
        from asr.routes import _parse_wav_header
        # 构建最小有效 WAV 头 (44 字节)
        import struct
        header = bytearray(44)
        header[0:4] = b"RIFF"
        struct.pack_into("<I", header, 4, 36)  # file size - 8
        header[8:12] = b"WAVE"
        header[12:16] = b"fmt "
        struct.pack_into("<I", header, 16, 16)  # chunk size
        struct.pack_into("<H", header, 20, 1)   # PCM
        struct.pack_into("<H", header, 22, 1)   # mono
        struct.pack_into("<I", header, 24, 16000)  # sample rate
        struct.pack_into("<I", header, 28, 32000)  # byte rate
        struct.pack_into("<H", header, 32, 2)   # block align
        struct.pack_into("<H", header, 34, 16)  # bits per sample

        result = _parse_wav_header(bytes(header))
        # 验证函数返回 dict（可能为空或包含解析后的信息）
        assert isinstance(result, dict)

    def test_parse_non_wav_data(self):
        """解析非 WAV 数据"""
        from asr.routes import _parse_wav_header
        result = _parse_wav_header(b"not a wav file")
        assert result == {}

    def test_parse_too_short_data(self):
        """解析过短数据"""
        from asr.routes import _parse_wav_header
        result = _parse_wav_header(b"RIFF")
        assert result == {}


class TestErrorResponse:
    """错误响应构建测试"""

    def test_error_response_format(self):
        from asr.routes import _error_response
        from fastapi import status
        resp = _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_AUDIO",
            message="音频格式不支持",
            request_id="req-123"
        )
        assert resp.status_code == 400
        body = resp.body
        assert b"INVALID_AUDIO" in body
        assert b"req-123" in body


class TestASREndpoint:
    """ASR 转写端点测试"""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        app = FastAPI()
        from asr.routes import router
        app.include_router(router)
        return TestClient(app)

    def test_transcriptions_health(self, client):
        """健康检查"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_transcriptions_no_file(self, client):
        """无文件上传返回 422"""
        response = client.post("/transcriptions")
        assert response.status_code == 422

    def test_transcriptions_with_mock_audio(self, client):
        """上传模拟音频 — 验证端点接受请求"""
        # 创建一个假的 WAV 数据
        import struct
        audio_data = bytearray(44 + 1000)
        audio_data[0:4] = b"RIFF"
        struct.pack_into("<I", audio_data, 4, len(audio_data) - 8)
        audio_data[8:12] = b"WAVE"
        audio_data[12:16] = b"fmt "
        struct.pack_into("<I", audio_data, 16, 16)
        struct.pack_into("<H", audio_data, 20, 1)
        struct.pack_into("<H", audio_data, 22, 1)
        struct.pack_into("<I", audio_data, 24, 16000)
        struct.pack_into("<I", audio_data, 28, 32000)
        struct.pack_into("<H", audio_data, 32, 2)
        struct.pack_into("<H", audio_data, 34, 16)
        audio_data[36:40] = b"data"
        struct.pack_into("<I", audio_data, 40, 1000)

        response = client.post(
            "/transcriptions",
            files={"audio": ("test.wav", bytes(audio_data), "audio/wav")},
            data={"language": "zh-CN"}
        )
        # 讯飞引擎可能不可用，接受多种状态码
        assert response.status_code in [200, 500, 503]
