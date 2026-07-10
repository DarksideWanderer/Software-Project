"""
backend-core 数据模型单元测试
测试 schemas/device.py 中的 Pydantic 模型
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from pydantic import ValidationError


class TestCommandRequest:
    """CommandRequest 模型测试"""

    def test_create_with_required_fields(self):
        from app.schemas.device import CommandRequest
        req = CommandRequest(command="turn_on")
        assert req.command == "turn_on"
        assert req.params == {}

    def test_create_with_params(self):
        from app.schemas.device import CommandRequest
        req = CommandRequest(command="set_temperature", params={"temperature": 26})
        assert req.command == "set_temperature"
        assert req.params == {"temperature": 26}

    def test_missing_command_raises_error(self):
        from app.schemas.device import CommandRequest
        with pytest.raises(ValidationError):
            CommandRequest()

    def test_params_defaults_to_empty_dict(self):
        from app.schemas.device import CommandRequest
        req = CommandRequest(command="turn_off")
        assert req.params == {}

    def test_command_with_complex_params(self):
        from app.schemas.device import CommandRequest
        req = CommandRequest(
            command="set_color",
            params={"color": "warm", "transition": 3000}
        )
        assert req.params["color"] == "warm"
        assert req.params["transition"] == 3000


class TestCommandResponse:
    """CommandResponse 模型测试"""

    def test_default_values(self):
        from app.schemas.device import CommandResponse
        resp = CommandResponse()
        assert resp.success is False
        assert resp.message == ""
        assert resp.state is None

    def test_success_response(self):
        from app.schemas.device import CommandResponse
        resp = CommandResponse(
            success=True,
            message="ok",
            state={"is_on": True, "temperature": 26}
        )
        assert resp.success is True
        assert resp.message == "ok"
        assert resp.state == {"is_on": True, "temperature": 26}

    def test_failure_response(self):
        from app.schemas.device import CommandResponse
        resp = CommandResponse(
            success=False,
            message="Device not connected"
        )
        assert resp.success is False
        assert resp.message == "Device not connected"

    def test_state_is_optional(self):
        from app.schemas.device import CommandResponse
        resp = CommandResponse(success=True, message="done")
        assert resp.state is None
