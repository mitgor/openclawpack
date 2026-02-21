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
