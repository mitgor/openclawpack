"""Tests for the transport exception hierarchy.

Verifies:
- All exceptions inherit from TransportError
- Each exception is independently catchable
- String representations include context fields
- TransportError works as a catch-all
"""

from __future__ import annotations

import pytest

from openclawpack.transport.errors import (
    CLINotFound,
    ConnectionError_,
    JSONDecodeError,
    ProcessError,
    TransportError,
    TransportTimeout,
)


# ── Inheritance tests ─────────────────────────────────────────────

class TestInheritance:
    """All transport exceptions must inherit from TransportError."""

    @pytest.mark.parametrize(
        "exc_cls",
        [CLINotFound, ProcessError, TransportTimeout, JSONDecodeError, ConnectionError_],
    )
    def test_is_subclass_of_transport_error(self, exc_cls: type) -> None:
        assert issubclass(exc_cls, TransportError)

    @pytest.mark.parametrize(
        "exc_cls",
        [CLINotFound, ProcessError, TransportTimeout, JSONDecodeError, ConnectionError_],
    )
    def test_is_subclass_of_exception(self, exc_cls: type) -> None:
        assert issubclass(exc_cls, Exception)


# ── Independent catchability tests ────────────────────────────────

class TestIndependentCatch:
    """Each exception type must be catchable independently."""

    def test_cli_not_found_not_caught_by_process_error(self) -> None:
        with pytest.raises(CLINotFound):
            try:
                raise CLINotFound()
            except ProcessError:
                pytest.fail("CLINotFound should not be caught by ProcessError")

    def test_process_error_not_caught_by_cli_not_found(self) -> None:
        with pytest.raises(ProcessError):
            try:
                raise ProcessError()
            except CLINotFound:
                pytest.fail("ProcessError should not be caught by CLINotFound")

    def test_timeout_not_caught_by_json_decode(self) -> None:
        with pytest.raises(TransportTimeout):
            try:
                raise TransportTimeout()
            except JSONDecodeError:
                pytest.fail("TransportTimeout should not be caught by JSONDecodeError")

    def test_json_decode_not_caught_by_timeout(self) -> None:
        with pytest.raises(JSONDecodeError):
            try:
                raise JSONDecodeError()
            except TransportTimeout:
                pytest.fail("JSONDecodeError should not be caught by TransportTimeout")

    def test_connection_error_not_caught_by_process_error(self) -> None:
        with pytest.raises(ConnectionError_):
            try:
                raise ConnectionError_()
            except ProcessError:
                pytest.fail("ConnectionError_ should not be caught by ProcessError")


# ── Catch-all tests ──────────────────────────────────────────────

class TestCatchAll:
    """TransportError catches all transport exceptions."""

    @pytest.mark.parametrize(
        "exc_cls",
        [CLINotFound, ProcessError, TransportTimeout, JSONDecodeError, ConnectionError_],
    )
    def test_transport_error_catches_all(self, exc_cls: type) -> None:
        with pytest.raises(TransportError):
            raise exc_cls()


# ── String representation tests ───────────────────────────────────

class TestStringRepresentation:
    """Exception __str__ includes stored context fields."""

    def test_transport_error_default_message(self) -> None:
        e = TransportError()
        assert "Transport operation failed" in str(e)

    def test_transport_error_custom_message(self) -> None:
        e = TransportError("something broke")
        assert "something broke" in str(e)

    def test_cli_not_found_includes_install_suggestion(self) -> None:
        e = CLINotFound()
        s = str(e)
        assert "Claude Code CLI not found" in s
        assert "npm install" in s

    def test_process_error_includes_exit_code(self) -> None:
        e = ProcessError("failed", exit_code=42)
        s = str(e)
        assert "exit_code=42" in s

    def test_process_error_includes_stderr(self) -> None:
        e = ProcessError("failed", stderr="bad stuff")
        s = str(e)
        assert "bad stuff" in s

    def test_process_error_default_no_extra_context(self) -> None:
        e = ProcessError()
        s = str(e)
        assert "exit_code" not in s
        assert "stderr" not in s

    def test_timeout_includes_seconds(self) -> None:
        e = TransportTimeout("timed out", timeout_seconds=60.0)
        s = str(e)
        assert "timeout_seconds=60.0" in s

    def test_timeout_default_no_seconds(self) -> None:
        e = TransportTimeout()
        s = str(e)
        assert "timeout_seconds" not in s

    def test_json_decode_includes_raw_output(self) -> None:
        e = JSONDecodeError("bad json", raw_output='{"broken')
        s = str(e)
        assert '{"broken' in s

    def test_json_decode_truncates_long_output(self) -> None:
        long_output = "x" * 500
        e = JSONDecodeError("bad json", raw_output=long_output)
        s = str(e)
        assert "..." in s
        # The repr of a 200-char string + "..." should be shorter than 500 chars
        assert len(s) < 500

    def test_connection_error_message(self) -> None:
        e = ConnectionError_()
        assert "Connection to Claude Code subprocess lost" in str(e)


# ── Context field storage tests ───────────────────────────────────

class TestContextFields:
    """Exceptions store their context fields as attributes."""

    def test_process_error_stores_exit_code(self) -> None:
        e = ProcessError("fail", exit_code=1)
        assert e.exit_code == 1

    def test_process_error_stores_stderr(self) -> None:
        e = ProcessError("fail", stderr="error output")
        assert e.stderr == "error output"

    def test_process_error_defaults(self) -> None:
        e = ProcessError()
        assert e.exit_code is None
        assert e.stderr is None

    def test_timeout_stores_seconds(self) -> None:
        e = TransportTimeout("timeout", timeout_seconds=30.5)
        assert e.timeout_seconds == 30.5

    def test_json_decode_stores_raw_output(self) -> None:
        e = JSONDecodeError("decode fail", raw_output="raw")
        assert e.raw_output == "raw"

    def test_json_decode_default_raw_output(self) -> None:
        e = JSONDecodeError()
        assert e.raw_output is None

    def test_all_exceptions_store_message(self) -> None:
        e = TransportError("msg1")
        assert e.message == "msg1"
        e2 = CLINotFound("msg2")
        assert e2.message == "msg2"
        e3 = ProcessError("msg3")
        assert e3.message == "msg3"
