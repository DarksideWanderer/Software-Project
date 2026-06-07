import pytest

from app.llm_nlu import parse_deepseek_content
from app.nlu import parse_text
from app.schemas import NluResponse, Slots


def test_parse_deepseek_content_to_nlu_response():
    result = parse_deepseek_content(
        """
        {
          "success": true,
          "intent": "device_control",
          "confidence": 0.82,
          "slots": {
            "device_type": "air_conditioner",
            "location": "bedroom",
            "action": "increase_temperature",
            "value": 2,
            "unit": "celsius"
          },
          "need_clarification": false,
          "reply": "好的，已识别为调高卧室空调温度。"
        }
        """
    )

    assert result.intent == "device_control"
    assert result.slots.device_type == "air_conditioner"
    assert result.slots.location == "bedroom"
    assert result.slots.action == "increase_temperature"
    assert result.slots.value == 2


def test_parse_deepseek_content_rejects_invalid_json():
    with pytest.raises(ValueError):
        parse_deepseek_content("not json")


def test_nlu_uses_rule_result_when_deepseek_not_configured():
    result = parse_text("给我讲个故事")

    assert result.intent == "unknown"


def test_nlu_uses_deepseek_for_unknown_when_configured(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    def fake_parse_with_deepseek(text, context):
        return NluResponse(
            success=True,
            intent="device_control",
            confidence=0.86,
            slots=Slots(
                device_type="air_conditioner",
                location="bedroom",
                action="increase_temperature",
                value=1,
                unit="celsius",
            ),
            need_clarification=False,
            reply="好的，已识别为调高卧室空调温度。",
        )

    monkeypatch.setattr("app.nlu.llm_nlu.parse_with_deepseek", fake_parse_with_deepseek)

    result = parse_text("我有点冷，把卧室弄暖和一点")

    assert result.intent == "device_control"
    assert result.slots.device_type == "air_conditioner"
    assert result.slots.location == "bedroom"
    assert result.slots.action == "increase_temperature"


def test_nlu_falls_back_to_rules_when_deepseek_fails(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    def fake_parse_with_deepseek(text, context):
        raise RuntimeError("provider failed")

    monkeypatch.setattr("app.nlu.llm_nlu.parse_with_deepseek", fake_parse_with_deepseek)

    result = parse_text("给我讲个故事")

    assert result.intent == "unknown"
