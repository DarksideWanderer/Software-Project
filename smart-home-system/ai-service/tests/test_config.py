from app.config import Settings


def test_settings_reads_iflytek_environment(monkeypatch):
    monkeypatch.setenv("IFLYTEK_APP_ID", "test_app_id")
    monkeypatch.setenv("IFLYTEK_API_KEY", "test_api_key")
    monkeypatch.setenv("IFLYTEK_API_SECRET", "test_api_secret")

    settings = Settings()

    assert settings.iflytek_app_id == "test_app_id"
    assert settings.iflytek_api_key == "test_api_key"
    assert settings.iflytek_api_secret == "test_api_secret"


def test_settings_reads_deepseek_environment(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test_deepseek_key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.com")

    settings = Settings()

    assert settings.deepseek_api_key == "test_deepseek_key"
    assert settings.deepseek_model == "deepseek-v4-pro"
    assert settings.deepseek_base_url == "https://example.com"


def test_settings_falls_back_to_llm_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "legacy_llm_key")

    settings = Settings()

    assert settings.deepseek_api_key == "legacy_llm_key"
