"""Tests for CommandResult output schema."""

import json

from openclawpack.output.schema import CommandResult


class TestCommandResultOk:
    """Tests for successful CommandResult creation."""

    def test_ok_has_success_true(self) -> None:
        result = CommandResult.ok(result={"phase": 1})
        assert result.success is True

    def test_ok_has_empty_errors(self) -> None:
        result = CommandResult.ok(result={"phase": 1})
        assert result.errors == []

    def test_ok_stores_result(self) -> None:
        data = {"phase": 1, "status": "running"}
        result = CommandResult.ok(result=data)
        assert result.result == data

    def test_ok_with_session_and_usage(self) -> None:
        result = CommandResult.ok(
            result="done",
            session_id="abc-123",
            usage={"input_tokens": 100, "output_tokens": 50},
            duration_ms=1500,
        )
        assert result.session_id == "abc-123"
        assert result.usage == {"input_tokens": 100, "output_tokens": 50}
        assert result.duration_ms == 1500


class TestCommandResultError:
    """Tests for error CommandResult creation."""

    def test_error_has_success_false(self) -> None:
        result = CommandResult.error("something broke")
        assert result.success is False

    def test_error_has_message_in_errors(self) -> None:
        result = CommandResult.error("something broke")
        assert "something broke" in result.errors

    def test_error_has_none_result(self) -> None:
        result = CommandResult.error("something broke")
        assert result.result is None

    def test_error_with_duration(self) -> None:
        result = CommandResult.error("timeout", duration_ms=5000)
        assert result.duration_ms == 5000


class TestCommandResultSerialization:
    """Tests for JSON serialization."""

    def test_to_json_returns_valid_json(self) -> None:
        result = CommandResult.ok(result={"test": True})
        parsed = json.loads(result.to_json())
        assert isinstance(parsed, dict)

    def test_to_json_has_all_six_top_level_keys(self) -> None:
        result = CommandResult.ok(result={"test": True})
        parsed = json.loads(result.to_json())
        expected_keys = {"success", "result", "errors", "session_id", "usage", "duration_ms"}
        assert set(parsed.keys()) == expected_keys

    def test_model_json_schema_has_all_fields(self) -> None:
        schema = CommandResult.model_json_schema()
        assert "properties" in schema
        expected_fields = {"success", "result", "errors", "session_id", "usage", "duration_ms"}
        assert expected_fields == set(schema["properties"].keys())

    def test_round_trip_preserves_data(self) -> None:
        original = CommandResult.ok(
            result={"phase": 1, "items": [1, 2, 3]},
            session_id="sess-456",
            usage={"tokens": 200},
            duration_ms=750,
        )
        json_str = original.to_json()
        restored = CommandResult.model_validate_json(json_str)

        assert restored.success == original.success
        assert restored.result == original.result
        assert restored.errors == original.errors
        assert restored.session_id == original.session_id
        assert restored.usage == original.usage
        assert restored.duration_ms == original.duration_ms

    def test_error_round_trip(self) -> None:
        original = CommandResult.error("bad input", duration_ms=100)
        json_str = original.to_json()
        restored = CommandResult.model_validate_json(json_str)

        assert restored.success is False
        assert restored.errors == ["bad input"]
        assert restored.duration_ms == 100
