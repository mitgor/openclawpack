"""Tests for the ClaudeTransport adapter.

Tests cover:
- Instantiation with default and custom config
- Lazy import behavior (SDK not loaded until ClaudeTransport accessed)
- TransportConfig defaults
- Integration test (slow-marked, requires Claude CLI on PATH)
"""

from __future__ import annotations

import shutil
import sys

import pytest


# ── Lazy import tests ────────────────────────────────────────────

class TestLazyImport:
    """Importing openclawpack.transport must NOT import claude_agent_sdk."""

    def test_import_transport_does_not_load_sdk(self) -> None:
        """Importing the transport package does not trigger SDK import."""
        # Remove any cached SDK modules to get a clean test
        sdk_modules = [k for k in sys.modules if k.startswith("claude_agent_sdk")]
        saved = {k: sys.modules.pop(k) for k in sdk_modules}

        # Also remove transport modules to force fresh import
        transport_modules = [
            k for k in sys.modules if k.startswith("openclawpack.transport")
        ]
        saved_transport = {k: sys.modules.pop(k) for k in transport_modules}

        try:
            import openclawpack.transport  # noqa: F811

            # After import, SDK should NOT be in sys.modules
            assert "claude_agent_sdk" not in sys.modules, (
                "claude_agent_sdk was imported when loading openclawpack.transport"
            )
        finally:
            # Restore all modules
            sys.modules.update(saved)
            sys.modules.update(saved_transport)

    def test_accessing_claude_transport_triggers_sdk_import(self) -> None:
        """Accessing ClaudeTransport attribute triggers the lazy import."""
        from openclawpack.transport import ClaudeTransport

        assert ClaudeTransport is not None
        assert "claude_agent_sdk" in sys.modules

    def test_bad_attribute_raises(self) -> None:
        """Accessing non-existent attribute raises AttributeError."""
        import openclawpack.transport

        with pytest.raises(AttributeError, match="no attribute"):
            _ = openclawpack.transport.NonExistentClass  # type: ignore[attr-defined]


# ── Direct exports tests ─────────────────────────────────────────

class TestDirectExports:
    """Errors and config types are directly importable (no lazy import)."""

    def test_transport_config_importable(self) -> None:
        from openclawpack.transport import TransportConfig

        assert TransportConfig is not None

    def test_errors_importable(self) -> None:
        from openclawpack.transport import (
            CLINotFound,
            ConnectionError_,
            JSONDecodeError,
            ProcessError,
            TransportError,
            TransportTimeout,
        )

        assert all([
            TransportError,
            CLINotFound,
            ProcessError,
            TransportTimeout,
            JSONDecodeError,
            ConnectionError_,
        ])


# ── TransportConfig defaults tests ───────────────────────────────

class TestTransportConfig:
    """TransportConfig provides sensible defaults."""

    def test_default_timeout(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig()
        assert config.timeout_seconds == 300.0

    def test_default_permission_mode(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig()
        assert config.permission_mode == "bypassPermissions"

    def test_default_cwd_is_none(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig()
        assert config.cwd is None

    def test_default_cli_path_is_none(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig()
        assert config.cli_path is None

    def test_default_allowed_tools_is_none(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig()
        assert config.allowed_tools is None

    def test_default_system_prompt_is_none(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig()
        assert config.system_prompt is None

    def test_custom_timeout(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig(timeout_seconds=60)
        assert config.timeout_seconds == 60

    def test_custom_cwd(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig(cwd="/tmp/test")
        assert config.cwd == "/tmp/test"

    def test_custom_allowed_tools(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig(allowed_tools=["Read", "Glob"])
        assert config.allowed_tools == ["Read", "Glob"]

    def test_default_setting_sources_is_none(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig()
        assert config.setting_sources is None

    def test_default_max_turns_is_none(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig()
        assert config.max_turns is None

    def test_default_max_budget_usd_is_none(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig()
        assert config.max_budget_usd is None

    def test_system_prompt_accepts_dict(self) -> None:
        from openclawpack.transport import TransportConfig

        preset = {"type": "preset", "preset": "claude_code", "append": "test"}
        config = TransportConfig(system_prompt=preset)
        assert config.system_prompt == preset

    def test_system_prompt_accepts_str(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig(system_prompt="You are a helper.")
        assert config.system_prompt == "You are a helper."

    def test_custom_setting_sources(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig(setting_sources=["project"])
        assert config.setting_sources == ["project"]

    def test_custom_max_turns(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig(max_turns=10)
        assert config.max_turns == 10

    def test_custom_max_budget_usd(self) -> None:
        from openclawpack.transport import TransportConfig

        config = TransportConfig(max_budget_usd=5.0)
        assert config.max_budget_usd == 5.0


# ── ClaudeTransport instantiation tests ──────────────────────────

class TestClaudeTransportInstantiation:
    """ClaudeTransport instantiates correctly with config."""

    def test_default_config(self) -> None:
        from openclawpack.transport import ClaudeTransport, TransportConfig

        transport = ClaudeTransport()
        assert isinstance(transport.config, TransportConfig)
        assert transport.config.timeout_seconds == 300.0

    def test_custom_config(self) -> None:
        from openclawpack.transport import ClaudeTransport, TransportConfig

        config = TransportConfig(timeout_seconds=60, cwd="/tmp")
        transport = ClaudeTransport(config)
        assert transport.config.timeout_seconds == 60
        assert transport.config.cwd == "/tmp"

    def test_none_config_uses_defaults(self) -> None:
        from openclawpack.transport import ClaudeTransport

        transport = ClaudeTransport(None)
        assert transport.config.timeout_seconds == 300.0
        assert transport.config.permission_mode == "bypassPermissions"

    def test_has_run_method(self) -> None:
        from openclawpack.transport import ClaudeTransport

        transport = ClaudeTransport()
        assert callable(transport.run)
        assert hasattr(transport.run, "__func__") or callable(transport.run)

    def test_has_run_sync_method(self) -> None:
        from openclawpack.transport import ClaudeTransport

        transport = ClaudeTransport()
        assert callable(transport.run_sync)


# ── ClaudeTransport.run() option forwarding tests (mocked SDK) ───

class TestClaudeTransportRunForwarding:
    """Test that run() forwards new config fields and kwargs to sdk_query."""

    @pytest.mark.anyio
    async def test_system_prompt_dict_forwarded(self) -> None:
        """system_prompt dict preset is set on options."""
        from unittest.mock import AsyncMock, patch

        from openclawpack.transport import ClaudeTransport, TransportConfig

        preset = {"type": "preset", "preset": "claude_code", "append": "test"}
        config = TransportConfig(system_prompt=preset)
        transport = ClaudeTransport(config)

        captured_kwargs: dict = {}

        async def fake_query(*, prompt, options, transport=None):
            captured_kwargs["prompt"] = prompt
            captured_kwargs["options"] = options
            from claude_agent_sdk import ResultMessage

            msg = ResultMessage.__new__(ResultMessage)
            msg.is_error = False
            msg.result = "ok"
            msg.session_id = "s1"
            msg.usage = {}
            msg.duration_ms = 1
            yield msg

        with patch("openclawpack.transport.client.sdk_query", side_effect=fake_query):
            await transport.run("test prompt")

        assert captured_kwargs["options"].system_prompt == preset

    @pytest.mark.anyio
    async def test_setting_sources_forwarded(self) -> None:
        """setting_sources from config is set on options."""
        from unittest.mock import patch

        from openclawpack.transport import ClaudeTransport, TransportConfig

        config = TransportConfig(setting_sources=["project"])
        transport = ClaudeTransport(config)

        captured_kwargs: dict = {}

        async def fake_query(*, prompt, options, transport=None):
            captured_kwargs["prompt"] = prompt
            captured_kwargs["options"] = options
            from claude_agent_sdk import ResultMessage

            msg = ResultMessage.__new__(ResultMessage)
            msg.is_error = False
            msg.result = "ok"
            msg.session_id = "s1"
            msg.usage = {}
            msg.duration_ms = 1
            yield msg

        with patch("openclawpack.transport.client.sdk_query", side_effect=fake_query):
            await transport.run("test prompt")

        assert captured_kwargs["options"].setting_sources == ["project"]

    @pytest.mark.anyio
    async def test_max_turns_forwarded(self) -> None:
        """max_turns from config is set on options."""
        from unittest.mock import patch

        from openclawpack.transport import ClaudeTransport, TransportConfig

        config = TransportConfig(max_turns=5)
        transport = ClaudeTransport(config)

        captured_kwargs: dict = {}

        async def fake_query(*, prompt, options, transport=None):
            captured_kwargs["prompt"] = prompt
            captured_kwargs["options"] = options
            from claude_agent_sdk import ResultMessage

            msg = ResultMessage.__new__(ResultMessage)
            msg.is_error = False
            msg.result = "ok"
            msg.session_id = "s1"
            msg.usage = {}
            msg.duration_ms = 1
            yield msg

        with patch("openclawpack.transport.client.sdk_query", side_effect=fake_query):
            await transport.run("test prompt")

        assert captured_kwargs["options"].max_turns == 5

    @pytest.mark.anyio
    async def test_max_budget_usd_forwarded(self) -> None:
        """max_budget_usd from config is set on options."""
        from unittest.mock import patch

        from openclawpack.transport import ClaudeTransport, TransportConfig

        config = TransportConfig(max_budget_usd=2.5)
        transport = ClaudeTransport(config)

        captured_kwargs: dict = {}

        async def fake_query(*, prompt, options, transport=None):
            captured_kwargs["prompt"] = prompt
            captured_kwargs["options"] = options
            from claude_agent_sdk import ResultMessage

            msg = ResultMessage.__new__(ResultMessage)
            msg.is_error = False
            msg.result = "ok"
            msg.session_id = "s1"
            msg.usage = {}
            msg.duration_ms = 1
            yield msg

        with patch("openclawpack.transport.client.sdk_query", side_effect=fake_query):
            await transport.run("test prompt")

        assert captured_kwargs["options"].max_budget_usd == 2.5

    @pytest.mark.anyio
    async def test_can_use_tool_forwarded(self) -> None:
        """can_use_tool is set on options object, not passed as sdk_query kwarg."""
        from collections.abc import AsyncIterable
        from unittest.mock import patch

        from openclawpack.transport import ClaudeTransport, TransportConfig

        async def my_can_use_tool(tool_name, tool_input, context):
            pass

        transport = ClaudeTransport(TransportConfig())

        captured_kwargs: dict = {}

        async def fake_query(*, prompt, options, transport=None):
            """Mock enforcing real sdk_query() signature -- keyword-only, 3 args max."""
            captured_kwargs["prompt"] = prompt
            captured_kwargs["options"] = options
            from claude_agent_sdk import ResultMessage

            msg = ResultMessage.__new__(ResultMessage)
            msg.is_error = False
            msg.result = "ok"
            msg.session_id = "s1"
            msg.usage = {}
            msg.duration_ms = 1
            yield msg

        with patch("openclawpack.transport.client.sdk_query", side_effect=fake_query):
            await transport.run("test", can_use_tool=my_can_use_tool)

        assert captured_kwargs["options"].can_use_tool is my_can_use_tool
        # Prompt should be AsyncIterable when can_use_tool is set
        assert isinstance(captured_kwargs["prompt"], AsyncIterable)

    @pytest.mark.anyio
    async def test_hooks_forwarded(self) -> None:
        """hooks are set on options object, not passed as sdk_query kwarg."""
        from unittest.mock import patch

        from openclawpack.transport import ClaudeTransport, TransportConfig

        async def pre_tool_use(input, tool_use_id, context):
            return {}

        hooks = {"PreToolUse": pre_tool_use}
        transport = ClaudeTransport(TransportConfig())

        captured_kwargs: dict = {}

        async def fake_query(*, prompt, options, transport=None):
            """Mock enforcing real sdk_query() signature -- keyword-only, 3 args max."""
            captured_kwargs["prompt"] = prompt
            captured_kwargs["options"] = options
            from claude_agent_sdk import ResultMessage

            msg = ResultMessage.__new__(ResultMessage)
            msg.is_error = False
            msg.result = "ok"
            msg.session_id = "s1"
            msg.usage = {}
            msg.duration_ms = 1
            yield msg

        with patch("openclawpack.transport.client.sdk_query", side_effect=fake_query):
            await transport.run("test", hooks=hooks)

        assert captured_kwargs["options"].hooks is hooks

    @pytest.mark.anyio
    async def test_can_use_tool_not_passed_when_none(self) -> None:
        """When not provided, can_use_tool and hooks remain None on options."""
        from unittest.mock import patch

        from openclawpack.transport import ClaudeTransport, TransportConfig

        transport = ClaudeTransport(TransportConfig())

        captured_kwargs: dict = {}

        async def fake_query(*, prompt, options, transport=None):
            """Mock enforcing real sdk_query() signature -- keyword-only, 3 args max."""
            captured_kwargs["prompt"] = prompt
            captured_kwargs["options"] = options
            from claude_agent_sdk import ResultMessage

            msg = ResultMessage.__new__(ResultMessage)
            msg.is_error = False
            msg.result = "ok"
            msg.session_id = "s1"
            msg.usage = {}
            msg.duration_ms = 1
            yield msg

        with patch("openclawpack.transport.client.sdk_query", side_effect=fake_query):
            await transport.run("test")

        assert captured_kwargs["options"].can_use_tool is None
        assert captured_kwargs["options"].hooks is None
        # Prompt should be plain string when can_use_tool is not set
        assert captured_kwargs["prompt"] == "test"

    @pytest.mark.anyio
    async def test_verbose_sets_stderr_callback(self) -> None:
        """verbose=True sets options.stderr to a callback."""
        from unittest.mock import patch

        from openclawpack.transport import ClaudeTransport, TransportConfig

        transport = ClaudeTransport(TransportConfig())

        captured_kwargs: dict = {}

        async def fake_query(*, prompt, options, transport=None):
            captured_kwargs["options"] = options
            from claude_agent_sdk import ResultMessage

            msg = ResultMessage.__new__(ResultMessage)
            msg.is_error = False
            msg.result = "ok"
            msg.session_id = "s1"
            msg.usage = {}
            msg.duration_ms = 1
            yield msg

        with patch("openclawpack.transport.client.sdk_query", side_effect=fake_query):
            await transport.run("test", verbose=True)

        assert callable(captured_kwargs["options"].stderr)

    @pytest.mark.anyio
    async def test_quiet_sets_stderr_none(self) -> None:
        """quiet=True explicitly sets options.stderr to None."""
        from unittest.mock import patch

        from openclawpack.transport import ClaudeTransport, TransportConfig

        transport = ClaudeTransport(TransportConfig())

        captured_kwargs: dict = {}

        async def fake_query(*, prompt, options, transport=None):
            captured_kwargs["options"] = options
            from claude_agent_sdk import ResultMessage

            msg = ResultMessage.__new__(ResultMessage)
            msg.is_error = False
            msg.result = "ok"
            msg.session_id = "s1"
            msg.usage = {}
            msg.duration_ms = 1
            yield msg

        with patch("openclawpack.transport.client.sdk_query", side_effect=fake_query):
            await transport.run("test", quiet=True)

        assert captured_kwargs["options"].stderr is None

    @pytest.mark.anyio
    async def test_quiet_takes_precedence_over_verbose(self) -> None:
        """When both quiet and verbose are set, quiet wins (stderr=None)."""
        from unittest.mock import patch

        from openclawpack.transport import ClaudeTransport, TransportConfig

        transport = ClaudeTransport(TransportConfig())

        captured_kwargs: dict = {}

        async def fake_query(*, prompt, options, transport=None):
            captured_kwargs["options"] = options
            from claude_agent_sdk import ResultMessage

            msg = ResultMessage.__new__(ResultMessage)
            msg.is_error = False
            msg.result = "ok"
            msg.session_id = "s1"
            msg.usage = {}
            msg.duration_ms = 1
            yield msg

        with patch("openclawpack.transport.client.sdk_query", side_effect=fake_query):
            await transport.run("test", verbose=True, quiet=True)

        assert captured_kwargs["options"].stderr is None


# ── Integration test (slow, requires Claude Code) ────────────────

@pytest.mark.slow
class TestClaudeTransportIntegration:
    """Integration tests requiring Claude Code CLI on PATH.

    Run with: pytest -m slow
    """

    @pytest.fixture(autouse=True)
    def _require_claude_cli(self) -> None:
        """Skip if Claude Code CLI is not available."""
        pytest.importorskip("claude_agent_sdk")
        if shutil.which("claude") is None:
            pytest.skip("Claude Code CLI not found on PATH")

    @pytest.mark.anyio
    async def test_trivial_prompt_completes(self) -> None:
        """Send a trivial prompt and verify it completes without deadlock.

        Covers TRNS-03: concurrent I/O prevents deadlock/hanging.
        """
        from openclawpack.transport import ClaudeTransport, TransportConfig

        config = TransportConfig(
            timeout_seconds=120,
            allowed_tools=[],
        )
        transport = ClaudeTransport(config)
        result = await transport.run("Respond with exactly: hello")

        assert result.success is True
        assert result.result is not None
        assert result.session_id is not None
        assert result.duration_ms >= 0
