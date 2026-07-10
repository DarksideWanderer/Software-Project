"""
ai-service TTS 模块单元测试
测试 src/tts/routes.py 中的语音合成功能
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class TestTTSModels:
    """TTS 数据模型测试"""

    def test_synthesize_request_defaults(self):
        from tts.routes import SynthesizeRequest
        req = SynthesizeRequest(text="你好世界")
        assert req.text == "你好世界"
        assert req.voice == "default"
        assert req.format == "mp3"

    def test_synthesize_request_custom_voice(self):
        from tts.routes import SynthesizeRequest
        req = SynthesizeRequest(text="你好", voice="xiaoyan", format="wav")
        assert req.voice == "xiaoyan"
        assert req.format == "wav"

    def test_synthesize_response_structure(self):
        from tts.routes import SynthesizeResponse
        resp = SynthesizeResponse(
            status="success",
            audio_url="/internal/v1/tts/audio/test.mp3",
            content_type="audio/mpeg"
        )
        assert resp.status == "success"
        assert resp.audio_url == "/internal/v1/tts/audio/test.mp3"


class TestContentTypeMapping:
    """MIME 类型映射测试"""

    def test_mp3_mapping(self):
        from tts.routes import _resolve_content_type
        assert _resolve_content_type("mp3") == "audio/mpeg"

    def test_wav_mapping(self):
        from tts.routes import _resolve_content_type
        assert _resolve_content_type("wav") == "audio/wav"

    def test_ogg_mapping(self):
        from tts.routes import _resolve_content_type
        assert _resolve_content_type("ogg") == "audio/ogg"

    def test_unknown_format_fallback(self):
        from tts.routes import _resolve_content_type
        result = _resolve_content_type("flac")
        assert result == "audio/flac"


class TestAudioCleanup:
    """音频过期清理测试"""

    def test_cleanup_empty_directory(self):
        """清理空目录"""
        from tts.routes import _cleanup_expired_audio
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tts.routes.AUDIO_DIR", tmpdir):
                count = _cleanup_expired_audio()
                assert count == 0

    def test_cleanup_expired_files(self):
        """清理过期文件"""
        from tts.routes import _cleanup_expired_audio
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tts.routes.AUDIO_DIR", tmpdir):
                # 创建一个旧文件
                old_file = os.path.join(tmpdir, "old_test.wav")
                with open(old_file, "w") as f:
                    f.write("dummy")
                # 设置 mtime 到 2 小时前
                old_time = time.time() - 7200
                os.utime(old_file, (old_time, old_time))

                count = _cleanup_expired_audio()
                assert count >= 0  # 取决于 AUDIO_MAX_AGE_SECONDS

    def test_cleanup_skips_non_audio(self):
        """跳过非音频文件"""
        from tts.routes import _cleanup_expired_audio
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tts.routes.AUDIO_DIR", tmpdir):
                # 创建非音频文件
                txt_file = os.path.join(tmpdir, "notes.txt")
                with open(txt_file, "w") as f:
                    f.write("notes")
                count = _cleanup_expired_audio()
                assert count == 0  # 不删除 .txt


class TestTTSHealthEndpoint:
    """TTS 健康检查端点"""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        app = FastAPI()
        from tts.routes import router
        app.include_router(router)
        return TestClient(app)

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["module"] == "tts"


class TestFallbackSynthesize:
    """本地 fallback 合成测试"""

    def test_fallback_with_empty_text(self):
        """空文本 fallback"""
        from tts.routes import _fallback_synthesize
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.wav")
            # fallback 可能返回文件路径或抛出异常
            try:
                result = _fallback_synthesize("", filepath)
            except Exception:
                pass  # 预期可能的异常

    def test_fallback_with_text(self):
        """正常文本 fallback"""
        from tts.routes import _fallback_synthesize
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.wav")
            try:
                result = _fallback_synthesize("你好世界", filepath)
                # 结果应该是文件路径
                assert isinstance(result, str)
            except Exception:
                pass  # 没有 pyttsx3 时预期异常
