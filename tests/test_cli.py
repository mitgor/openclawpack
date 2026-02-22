"""Tests for CLI argument parsing and option placement.

Verifies both gap fixes from 02-VERIFICATION.md:
1. --idea as a named option on new-project (alongside positional argument)
2. --project-dir, --verbose, --quiet as per-command options on all commands

All tests mock workflow functions -- no real Claude Code invocations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from openclawpack.cli import app
from openclawpack.output.schema import CommandResult

runner = CliRunner()


# ── Helpers ──────────────────────────────────────────────────────


def _ok_result() -> CommandResult:
    """Return a minimal successful CommandResult."""
    return CommandResult.ok(result={"status": "ok"}, duration_ms=1)


def _mock_engine() -> MagicMock:
    """Create a mock WorkflowEngine whose run_gsd_command returns ok."""
    engine = MagicMock()
    engine.run_gsd_command = AsyncMock(return_value=_ok_result())
    return engine


# Patch targets for workflow functions (at source module)
_NEW_PROJECT_WF = "openclawpack.commands.new_project.new_project_workflow"
_STATUS_WF = "openclawpack.commands.status.status_workflow"
_PLAN_PHASE_WF = "openclawpack.commands.plan_phase.plan_phase_workflow"
_EXECUTE_PHASE_WF = "openclawpack.commands.execute_phase.execute_phase_workflow"

# Patch target for WorkflowEngine (used by all async workflows)
_ENGINE_PATCH = "openclawpack.commands.engine.WorkflowEngine"


# ── TestNewProjectIdeaFlag ───────────────────────────────────────


class TestNewProjectIdeaFlag:
    """Tests for the --idea named option on new-project command."""

    def test_idea_as_named_option(self) -> None:
        """new-project --idea 'text' should parse and call workflow with idea text."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            result = runner.invoke(app, ["new-project", "--idea", "build a todo app"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"

    def test_idea_as_positional_arg(self) -> None:
        """new-project 'text' (positional) should still work for backward compat."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            result = runner.invoke(app, ["new-project", "build a todo app"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"

    def test_idea_option_takes_precedence(self) -> None:
        """When both positional and --idea provided, --idea takes precedence."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()) as mock_cls:
            result = runner.invoke(
                app,
                ["new-project", "ignored positional", "--idea", "preferred"],
            )
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        # The workflow should have been called with idea="preferred"
        mock_engine = mock_cls.return_value
        call_kwargs = mock_engine.run_gsd_command.call_args
        # run_gsd_command is called with command= and prompt= kwargs
        # The prompt should contain the preferred idea text
        prompt_text = call_kwargs[1].get("prompt", "") if call_kwargs[1] else ""
        if not prompt_text and call_kwargs[0]:
            prompt_text = str(call_kwargs)
        assert "preferred" in str(call_kwargs), (
            f"Expected 'preferred' in workflow call, got: {call_kwargs}"
        )

    def test_no_idea_errors(self) -> None:
        """new-project with no idea argument and no --idea should fail."""
        result = runner.invoke(app, ["new-project"])
        assert result.exit_code != 0, (
            f"Expected non-zero exit code, got {result.exit_code}"
        )


# ── TestPerCommandOptions ────────────────────────────────────────


class TestPerCommandOptions:
    """Tests for --project-dir, --verbose, --quiet placed after subcommand."""

    def test_status_project_dir_after_subcommand(self) -> None:
        """status --project-dir . should parse (options after subcommand)."""
        with patch(_STATUS_WF, return_value=_ok_result()) as mock_wf:
            result = runner.invoke(app, ["status", "--project-dir", "/tmp"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        mock_wf.assert_called_once()
        assert mock_wf.call_args[1]["project_dir"] == "/tmp"

    def test_plan_phase_verbose_after_subcommand(self) -> None:
        """plan-phase --verbose 1 should parse without exit code 2."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            result = runner.invoke(app, ["plan-phase", "--verbose", "1"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"

    def test_execute_phase_quiet_after_subcommand(self) -> None:
        """execute-phase --quiet 1 should parse without exit code 2."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            result = runner.invoke(app, ["execute-phase", "--quiet", "1"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"

    def test_global_project_dir_still_works(self) -> None:
        """--project-dir before subcommand (global) should still work."""
        with patch(_STATUS_WF, return_value=_ok_result()) as mock_wf:
            result = runner.invoke(app, ["--project-dir", "/tmp", "status"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        mock_wf.assert_called_once()
        assert mock_wf.call_args[1]["project_dir"] == "/tmp"

    def test_new_project_verbose_after_subcommand(self) -> None:
        """new-project --verbose --idea 'text' should parse correctly."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            result = runner.invoke(
                app, ["new-project", "--verbose", "--idea", "test idea"]
            )
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"

    def test_new_project_project_dir_after_subcommand(self) -> None:
        """new-project --project-dir /tmp --idea 'text' should parse correctly."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            result = runner.invoke(
                app,
                ["new-project", "--project-dir", "/tmp", "--idea", "test idea"],
            )
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"

    def test_status_quiet_after_subcommand(self) -> None:
        """status --quiet should suppress output."""
        with patch(_STATUS_WF, return_value=_ok_result()):
            result = runner.invoke(app, ["status", "--quiet"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        # With --quiet, no JSON output should be printed
        assert result.output.strip() == ""

    def test_execute_phase_project_dir_after_subcommand(self) -> None:
        """execute-phase --project-dir /tmp 1 should parse correctly."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            result = runner.invoke(
                app, ["execute-phase", "--project-dir", "/tmp", "1"]
            )
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"


# ── TestOutputFormat ─────────────────────────────────────────────


class TestOutputFormat:
    """Tests for --output-format flag."""

    def test_output_format_flag_in_global_help(self) -> None:
        """--output-format appears in global help."""
        result = runner.invoke(app, ["--help"])
        assert "--output-format" in result.output

    def test_output_format_json_default_status(self) -> None:
        """Default output format is JSON (contains 'success' key)."""
        with patch(_STATUS_WF, return_value=_ok_result()):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert '"success"' in result.output

    def test_output_format_text_status(self) -> None:
        """--output-format text produces human-readable output."""
        with patch(_STATUS_WF, return_value=_ok_result()):
            result = runner.invoke(
                app, ["--output-format", "text", "status"]
            )
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert "Status: SUCCESS" in result.output
        # Should NOT be JSON
        assert '"success"' not in result.output

    def test_output_format_text_with_usage(self) -> None:
        """--output-format text shows Tokens and Cost when usage is present."""
        ok_with_usage = CommandResult.ok(
            result="project info",
            usage={
                "input_tokens": 1500,
                "output_tokens": 300,
                "total_cost_usd": 0.0123,
            },
            duration_ms=5000,
        )
        with patch(_STATUS_WF, return_value=ok_with_usage):
            result = runner.invoke(
                app, ["--output-format", "text", "status"]
            )
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert "Tokens: 1,500 input / 300 output" in result.output
        assert "Cost: $0.0123" in result.output

    def test_output_format_text_new_project(self) -> None:
        """--output-format text works on new-project command."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            result = runner.invoke(
                app,
                ["--output-format", "text", "new-project", "--idea", "test idea"],
            )
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert "Status: SUCCESS" in result.output

    def test_output_format_text_plan_phase(self) -> None:
        """--output-format text works on plan-phase command."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            result = runner.invoke(
                app, ["--output-format", "text", "plan-phase", "1"]
            )
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert "Status: SUCCESS" in result.output

    def test_output_format_text_execute_phase(self) -> None:
        """--output-format text works on execute-phase command."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            result = runner.invoke(
                app, ["--output-format", "text", "execute-phase", "1"]
            )
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert "Status: SUCCESS" in result.output


# ── TestStatusZeroUsage ──────────────────────────────────────────


class TestStatusZeroUsage:
    """Status command returns zero usage instead of None."""

    def test_status_has_zero_usage(self) -> None:
        """Status command fills in zero usage when workflow returns None."""
        ok_no_usage = CommandResult.ok(result="info", duration_ms=10)
        assert ok_no_usage.usage is None  # Confirm starting state

        with patch(_STATUS_WF, return_value=ok_no_usage):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        # The JSON should contain usage with zero tokens
        import json

        parsed = json.loads(result.output)
        assert parsed["usage"] is not None
        assert parsed["usage"]["input_tokens"] == 0
        assert parsed["usage"]["output_tokens"] == 0
        assert parsed["usage"]["total_cost_usd"] == 0.0

    def test_status_text_format_has_zero_usage(self) -> None:
        """Status command with --output-format text shows zero tokens."""
        ok_no_usage = CommandResult.ok(result="info", duration_ms=10)
        with patch(_STATUS_WF, return_value=ok_no_usage):
            result = runner.invoke(
                app, ["--output-format", "text", "status"]
            )
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert "Tokens: 0 input / 0 output" in result.output
        assert "Cost: $0.0000" in result.output


# ── TestResumeFlag ───────────────────────────────────────────────


class TestResumeFlag:
    """Tests for --resume flag on CLI commands."""

    def test_resume_in_new_project_help(self) -> None:
        result = runner.invoke(app, ["new-project", "--help"])
        assert "--resume" in result.output

    def test_resume_in_plan_phase_help(self) -> None:
        result = runner.invoke(app, ["plan-phase", "--help"])
        assert "--resume" in result.output

    def test_resume_in_execute_phase_help(self) -> None:
        result = runner.invoke(app, ["execute-phase", "--help"])
        assert "--resume" in result.output

    def test_resume_not_in_status_help(self) -> None:
        """Status is local-only -- no --resume flag."""
        result = runner.invoke(app, ["status", "--help"])
        assert "--resume" not in result.output


# ── TestPackageImports ──────────────────────────────────────────


class TestPackageImports:
    """Tests for lazy __getattr__ re-exports in openclawpack.__init__."""

    def test_version_still_works(self) -> None:
        """openclawpack --version still works (PKG-04)."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "openclawpack" in result.output

    def test_import_create_project(self) -> None:
        from openclawpack import create_project

        import inspect

        assert inspect.iscoroutinefunction(create_project)

    def test_import_event_types(self) -> None:
        from openclawpack import EventBus, EventType, Event

        assert EventBus is not None
        assert EventType is not None
        assert Event is not None

    def test_import_get_status_is_coroutine(self) -> None:
        from openclawpack import get_status

        import inspect

        assert inspect.iscoroutinefunction(get_status)

    def test_nonexistent_attribute_raises(self) -> None:
        import openclawpack

        with pytest.raises(AttributeError):
            _ = openclawpack.nonexistent_attribute

    def test_all_contains_expected_names(self) -> None:
        import openclawpack

        expected = {
            "__version__",
            "create_project",
            "plan_phase",
            "execute_phase",
            "get_status",
            "add_project",
            "list_projects",
            "remove_project",
            "EventBus",
            "EventType",
            "Event",
        }
        assert expected == set(openclawpack.__all__)


# ── TestProjectsSubcommand ──────────────────────────────────────


class TestProjectsSubcommand:
    """Tests for projects subcommand registration."""

    def test_projects_help(self) -> None:
        """openclawpack projects --help shows add, list, remove."""
        result = runner.invoke(app, ["projects", "--help"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output

    def test_projects_in_main_help(self) -> None:
        """openclawpack --help shows projects subcommand."""
        result = runner.invoke(app, ["--help"])
        assert "projects" in result.output


# ── TestMakeCliBus ──────────────────────────────────────────────


class TestMakeCliBus:
    """Tests for _make_cli_bus helper."""

    def test_returns_event_bus(self) -> None:
        from openclawpack.cli import _make_cli_bus
        from openclawpack.events import EventBus

        bus = _make_cli_bus()
        assert isinstance(bus, EventBus)

    def test_all_event_types_registered(self) -> None:
        from openclawpack.cli import _make_cli_bus
        from openclawpack.events import EventType

        bus = _make_cli_bus()
        assert len(bus._handlers) == len(EventType)
        for event_type in EventType:
            assert event_type in bus._handlers
            assert len(bus._handlers[event_type]) == 1


# ── TestCliEventBusWiring ──────────────────────────────────────


class TestCliEventBusWiring:
    """Tests for event bus wiring in CLI commands."""

    def test_quiet_mode_no_bus_created(self) -> None:
        """When --quiet is set, no EventBus should be created."""
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            with patch("openclawpack.cli._make_cli_bus") as mock_bus:
                result = runner.invoke(
                    app, ["new-project", "--quiet", "--idea", "test"]
                )
            assert result.exit_code == 0
            mock_bus.assert_not_called()

    def test_normal_mode_bus_created(self) -> None:
        """Without --quiet, _make_cli_bus is called."""
        from openclawpack.events import EventBus

        real_bus = EventBus()
        with patch(_ENGINE_PATCH, return_value=_mock_engine()):
            with patch(
                "openclawpack.cli._make_cli_bus", return_value=real_bus
            ) as mock_bus:
                result = runner.invoke(
                    app, ["new-project", "--idea", "test"]
                )
            assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
            mock_bus.assert_called_once()
