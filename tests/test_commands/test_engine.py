"""Tests for the WorkflowEngine.

Tests use mocks for ClaudeTransport to avoid SDK/subprocess dependency.
Since engine.py uses local imports inside run_gsd_command(), we patch
the import source at ``openclawpack.transport.client.ClaudeTransport``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openclawpack.commands import DEFAULT_TIMEOUTS

_TRANSPORT_PATCH = "openclawpack.transport.client.ClaudeTransport"


# ── Prompt construction tests ────────────────────────────────────


class TestPromptConstruction:
    """WorkflowEngine constructs the correct prompt string per command."""

    @pytest.mark.anyio
    async def test_basic_command_prompt(self) -> None:
        """Command name is prefixed with / in the prompt."""
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine()

        captured: dict = {}

        async def mock_run(prompt, **kwargs):
            captured["prompt"] = prompt
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            instance = MockTransport.return_value
            instance.run = mock_run
            await engine.run_gsd_command("gsd:new-project")

        assert captured["prompt"] == "/gsd:new-project"

    @pytest.mark.anyio
    async def test_command_with_prompt_args(self) -> None:
        """prompt_args are appended after a space."""
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine()

        captured: dict = {}

        async def mock_run(prompt, **kwargs):
            captured["prompt"] = prompt
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            instance = MockTransport.return_value
            instance.run = mock_run
            await engine.run_gsd_command("gsd:plan-phase", prompt_args="3")

        assert captured["prompt"] == "/gsd:plan-phase 3"

    @pytest.mark.anyio
    async def test_prompt_override(self) -> None:
        """prompt_override replaces the constructed prompt entirely."""
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine()

        captured: dict = {}

        async def mock_run(prompt, **kwargs):
            captured["prompt"] = prompt
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            instance = MockTransport.return_value
            instance.run = mock_run
            await engine.run_gsd_command(
                "gsd:new-project",
                prompt_override="/custom prompt here",
            )

        assert captured["prompt"] == "/custom prompt here"


# ── Timeout tests ────────────────────────────────────────────────


class TestTimeoutSelection:
    """WorkflowEngine selects the correct default timeout per command."""

    @pytest.mark.anyio
    async def test_new_project_default_timeout(self) -> None:
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine()

        captured_config = {}

        async def mock_run(prompt, **kwargs):
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            def capture_init(config):
                captured_config["timeout"] = config.timeout_seconds
                mock_instance = MagicMock()
                mock_instance.run = mock_run
                return mock_instance

            MockTransport.side_effect = capture_init
            await engine.run_gsd_command("gsd:new-project")

        assert captured_config["timeout"] == 900

    @pytest.mark.anyio
    async def test_execute_phase_default_timeout(self) -> None:
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine()

        captured_config = {}

        async def mock_run(prompt, **kwargs):
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            def capture_init(config):
                captured_config["timeout"] = config.timeout_seconds
                mock_instance = MagicMock()
                mock_instance.run = mock_run
                return mock_instance

            MockTransport.side_effect = capture_init
            await engine.run_gsd_command("gsd:execute-phase")

        assert captured_config["timeout"] == 1200

    @pytest.mark.anyio
    async def test_custom_timeout_overrides_default(self) -> None:
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine(timeout=42)

        captured_config = {}

        async def mock_run(prompt, **kwargs):
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            def capture_init(config):
                captured_config["timeout"] = config.timeout_seconds
                mock_instance = MagicMock()
                mock_instance.run = mock_run
                return mock_instance

            MockTransport.side_effect = capture_init
            await engine.run_gsd_command("gsd:new-project")

        assert captured_config["timeout"] == 42

    @pytest.mark.anyio
    async def test_unknown_command_uses_600_default(self) -> None:
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine()

        captured_config = {}

        async def mock_run(prompt, **kwargs):
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            def capture_init(config):
                captured_config["timeout"] = config.timeout_seconds
                mock_instance = MagicMock()
                mock_instance.run = mock_run
                return mock_instance

            MockTransport.side_effect = capture_init
            await engine.run_gsd_command("gsd:unknown-command")

        assert captured_config["timeout"] == 600


# ── Config propagation tests ─────────────────────────────────────


class TestConfigPropagation:
    """WorkflowEngine propagates project_dir and system_prompt correctly."""

    @pytest.mark.anyio
    async def test_project_dir_becomes_cwd(self) -> None:
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine(project_dir="/my/project")

        captured_config = {}

        async def mock_run(prompt, **kwargs):
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            def capture_init(config):
                captured_config["cwd"] = config.cwd
                captured_config["system_prompt"] = config.system_prompt
                captured_config["setting_sources"] = config.setting_sources
                mock_instance = MagicMock()
                mock_instance.run = mock_run
                return mock_instance

            MockTransport.side_effect = capture_init
            await engine.run_gsd_command("gsd:new-project")

        assert captured_config["cwd"] == "/my/project"

    @pytest.mark.anyio
    async def test_system_prompt_is_preset_dict(self) -> None:
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine()

        captured_config = {}

        async def mock_run(prompt, **kwargs):
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            def capture_init(config):
                captured_config["system_prompt"] = config.system_prompt
                mock_instance = MagicMock()
                mock_instance.run = mock_run
                return mock_instance

            MockTransport.side_effect = capture_init
            await engine.run_gsd_command("gsd:new-project")

        sp = captured_config["system_prompt"]
        assert isinstance(sp, dict)
        assert sp["type"] == "preset"
        assert sp["preset"] == "claude_code"
        assert "non-interactively" in sp["append"]

    @pytest.mark.anyio
    async def test_setting_sources_is_project(self) -> None:
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine()

        captured_config = {}

        async def mock_run(prompt, **kwargs):
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            def capture_init(config):
                captured_config["setting_sources"] = config.setting_sources
                mock_instance = MagicMock()
                mock_instance.run = mock_run
                return mock_instance

            MockTransport.side_effect = capture_init
            await engine.run_gsd_command("gsd:new-project")

        assert captured_config["setting_sources"] == ["project"]


# ── Answer map wiring tests ──────────────────────────────────────


class TestAnswerMapWiring:
    """WorkflowEngine wires answer_map to can_use_tool callback."""

    @pytest.mark.anyio
    async def test_answer_map_creates_callback(self) -> None:
        """When answer_map provided, can_use_tool and hooks are passed to run()."""
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine()

        captured_kwargs: dict = {}

        async def mock_run(prompt, **kwargs):
            captured_kwargs.update(kwargs)
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            instance = MockTransport.return_value
            instance.run = mock_run
            await engine.run_gsd_command(
                "gsd:new-project",
                answer_map={"depth": "3"},
            )

        assert "can_use_tool" in captured_kwargs
        assert callable(captured_kwargs["can_use_tool"])
        assert "hooks" in captured_kwargs
        assert "PreToolUse" in captured_kwargs["hooks"]

    @pytest.mark.anyio
    async def test_no_answer_map_no_callback(self) -> None:
        """When answer_map is None, no can_use_tool or hooks are passed."""
        from openclawpack.commands.engine import WorkflowEngine

        engine = WorkflowEngine()

        captured_kwargs: dict = {}

        async def mock_run(prompt, **kwargs):
            captured_kwargs.update(kwargs)
            from openclawpack.output.schema import CommandResult

            return CommandResult.ok(result="done")

        with patch(_TRANSPORT_PATCH) as MockTransport:
            instance = MockTransport.return_value
            instance.run = mock_run
            await engine.run_gsd_command("gsd:new-project")

        assert "can_use_tool" not in captured_kwargs
        assert "hooks" not in captured_kwargs


# ── DEFAULT_TIMEOUTS tests ───────────────────────────────────────


class TestDefaultTimeouts:
    """DEFAULT_TIMEOUTS dict has expected entries."""

    def test_new_project_timeout(self) -> None:
        assert DEFAULT_TIMEOUTS["gsd:new-project"] == 900

    def test_plan_phase_timeout(self) -> None:
        assert DEFAULT_TIMEOUTS["gsd:plan-phase"] == 600

    def test_execute_phase_timeout(self) -> None:
        assert DEFAULT_TIMEOUTS["gsd:execute-phase"] == 1200
