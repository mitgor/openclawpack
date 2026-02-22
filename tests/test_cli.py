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
