"""Tests for the plan-phase workflow module.

Tests use mocks for WorkflowEngine.run_gsd_command to avoid SDK dependency.
Since plan_phase.py uses lazy imports (inside function body), we patch
WorkflowEngine at its source module: ``openclawpack.commands.engine``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from openclawpack.commands.plan_phase import (
    PLAN_PHASE_DEFAULTS,
    plan_phase_workflow,
)

_ENGINE_CLS_PATCH = "openclawpack.commands.engine.WorkflowEngine"
_ENGINE_RUN_PATCH = "openclawpack.commands.engine.WorkflowEngine.run_gsd_command"


# ── Prompt construction ─────────────────────────────────────────


class TestPromptConstruction:
    """plan_phase_workflow builds the correct prompt for the engine."""

    @pytest.mark.anyio
    async def test_plan_phase_prompt_construction(self) -> None:
        """Prompt is /gsd:plan-phase <N> for given phase number."""
        mock_run = AsyncMock()
        from openclawpack.output.schema import CommandResult

        mock_run.return_value = CommandResult.ok(result="planned")

        with patch(_ENGINE_RUN_PATCH, mock_run):
            await plan_phase_workflow(phase=2)

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.args[0] == "gsd:plan-phase"
        assert call_kwargs.kwargs["prompt_args"] == "2"

    @pytest.mark.anyio
    async def test_plan_phase_prompt_different_phase(self) -> None:
        """Phase number is converted to string in prompt_args."""
        mock_run = AsyncMock()
        from openclawpack.output.schema import CommandResult

        mock_run.return_value = CommandResult.ok(result="planned")

        with patch(_ENGINE_RUN_PATCH, mock_run):
            await plan_phase_workflow(phase=5)

        assert mock_run.call_args.kwargs["prompt_args"] == "5"


# ── Timeout tests ───────────────────────────────────────────────


class TestTimeout:
    """plan_phase_workflow uses correct default and custom timeouts."""

    @pytest.mark.anyio
    async def test_plan_phase_default_timeout(self) -> None:
        """Default timeout is 600s for plan-phase."""
        mock_run = AsyncMock()
        from openclawpack.output.schema import CommandResult

        mock_run.return_value = CommandResult.ok(result="planned")

        with patch(_ENGINE_CLS_PATCH) as MockEngine:
            mock_instance = MockEngine.return_value
            mock_instance.run_gsd_command = mock_run
            await plan_phase_workflow(phase=1)

        MockEngine.assert_called_once()
        assert MockEngine.call_args.kwargs["timeout"] == 600

    @pytest.mark.anyio
    async def test_plan_phase_custom_timeout(self) -> None:
        """Custom timeout overrides the 600s default."""
        mock_run = AsyncMock()
        from openclawpack.output.schema import CommandResult

        mock_run.return_value = CommandResult.ok(result="planned")

        with patch(_ENGINE_CLS_PATCH) as MockEngine:
            mock_instance = MockEngine.return_value
            mock_instance.run_gsd_command = mock_run
            await plan_phase_workflow(phase=1, timeout=300)

        assert MockEngine.call_args.kwargs["timeout"] == 300


# ── Answer map tests ────────────────────────────────────────────


class TestAnswerMap:
    """plan_phase_workflow builds and passes the correct answer map."""

    @pytest.mark.anyio
    async def test_plan_phase_default_answers(self) -> None:
        """PLAN_PHASE_DEFAULTS are passed as the answer_map."""
        mock_run = AsyncMock()
        from openclawpack.output.schema import CommandResult

        mock_run.return_value = CommandResult.ok(result="planned")

        with patch(_ENGINE_RUN_PATCH, mock_run):
            await plan_phase_workflow(phase=1)

        call_kwargs = mock_run.call_args.kwargs
        answer_map = call_kwargs["answer_map"]
        for key, value in PLAN_PHASE_DEFAULTS.items():
            assert answer_map[key] == value

    @pytest.mark.anyio
    async def test_plan_phase_answer_overrides(self) -> None:
        """answer_overrides merge on top of defaults."""
        mock_run = AsyncMock()
        from openclawpack.output.schema import CommandResult

        mock_run.return_value = CommandResult.ok(result="planned")

        with patch(_ENGINE_RUN_PATCH, mock_run):
            await plan_phase_workflow(
                phase=1,
                answer_overrides={"context": "Create", "custom": "value"},
            )

        call_kwargs = mock_run.call_args.kwargs
        answer_map = call_kwargs["answer_map"]
        # Override replaces default
        assert answer_map["context"] == "Create"
        # Other defaults preserved
        assert answer_map["confirm"] == "Yes"
        # Custom key added
        assert answer_map["custom"] == "value"


# ── Project dir propagation ─────────────────────────────────────


class TestProjectDirPropagation:
    """plan_phase_workflow passes project_dir through to WorkflowEngine."""

    @pytest.mark.anyio
    async def test_plan_phase_project_dir_propagation(self) -> None:
        """project_dir is forwarded to WorkflowEngine constructor."""
        mock_run = AsyncMock()
        from openclawpack.output.schema import CommandResult

        mock_run.return_value = CommandResult.ok(result="planned")

        with patch(_ENGINE_CLS_PATCH) as MockEngine:
            mock_instance = MockEngine.return_value
            mock_instance.run_gsd_command = mock_run
            await plan_phase_workflow(phase=1, project_dir="/my/project")

        assert MockEngine.call_args.kwargs["project_dir"] == "/my/project"

    @pytest.mark.anyio
    async def test_plan_phase_verbose_quiet_propagation(self) -> None:
        """verbose and quiet flags are forwarded to WorkflowEngine."""
        mock_run = AsyncMock()
        from openclawpack.output.schema import CommandResult

        mock_run.return_value = CommandResult.ok(result="planned")

        with patch(_ENGINE_CLS_PATCH) as MockEngine:
            mock_instance = MockEngine.return_value
            mock_instance.run_gsd_command = mock_run
            await plan_phase_workflow(phase=1, verbose=True, quiet=True)

        kwargs = MockEngine.call_args.kwargs
        assert kwargs["verbose"] is True
        assert kwargs["quiet"] is True
