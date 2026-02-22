"""Tests for the new-project command workflow.

All tests mock the transport layer -- no real Claude Code invocations.

NOTE: WorkflowEngine is imported lazily inside the function body, so we
patch at the source module (openclawpack.commands.engine.WorkflowEngine).
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openclawpack.commands.new_project import (
    NEW_PROJECT_DEFAULTS,
    new_project_workflow,
)
from openclawpack.output.schema import CommandResult

# Patch target for WorkflowEngine (source module, not consumer module)
_ENGINE_PATCH = "openclawpack.commands.engine.WorkflowEngine"


# ── Helper ───────────────────────────────────────────────────────


def _make_mock_engine() -> MagicMock:
    """Create a mock WorkflowEngine whose run_gsd_command returns a CommandResult."""
    engine = MagicMock()
    engine.run_gsd_command = AsyncMock(
        return_value=CommandResult.ok(result={"status": "created"}, duration_ms=100)
    )
    return engine


# ── Tests ────────────────────────────────────────────────────────


class TestNewProjectPrompt:
    @pytest.mark.anyio
    async def test_prompt_construction(self):
        """Prompt starts with /gsd:new-project --auto and contains the idea."""
        engine = _make_mock_engine()
        with patch(_ENGINE_PATCH, return_value=engine):
            await new_project_workflow(idea="build a todo app")
            engine.run_gsd_command.assert_called_once()
            call_kwargs = engine.run_gsd_command.call_args
            prompt = call_kwargs.kwargs.get("prompt_override")
            assert prompt is not None
            assert prompt.startswith("/gsd:new-project --auto")
            assert "build a todo app" in prompt

    @pytest.mark.anyio
    async def test_reads_idea_file(self):
        """If idea is a file path, its content is used in the prompt."""
        engine = _make_mock_engine()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("A machine learning pipeline for image classification")
            f.flush()
            idea_file = f.name

        try:
            with patch(_ENGINE_PATCH, return_value=engine):
                await new_project_workflow(idea=idea_file)
                call_kwargs = engine.run_gsd_command.call_args
                prompt = call_kwargs.kwargs.get("prompt_override")
                assert "machine learning pipeline" in prompt
                # Original file path should NOT be in the prompt
                assert idea_file not in prompt
        finally:
            Path(idea_file).unlink(missing_ok=True)

    @pytest.mark.anyio
    async def test_plain_text_idea(self):
        """Plain text that isn't a file path is used directly."""
        engine = _make_mock_engine()
        with patch(_ENGINE_PATCH, return_value=engine):
            await new_project_workflow(idea="build a REST API for user management")
            call_kwargs = engine.run_gsd_command.call_args
            prompt = call_kwargs.kwargs.get("prompt_override")
            assert "REST API for user management" in prompt


class TestNewProjectAnswerMap:
    @pytest.mark.anyio
    async def test_default_answers(self):
        """NEW_PROJECT_DEFAULTS is used when no overrides provided."""
        engine = _make_mock_engine()
        with patch(_ENGINE_PATCH, return_value=engine):
            await new_project_workflow(idea="test project")
            call_kwargs = engine.run_gsd_command.call_args
            answer_map = call_kwargs.kwargs.get("answer_map")
            assert answer_map is not None
            # Should contain all defaults
            for key, value in NEW_PROJECT_DEFAULTS.items():
                assert answer_map[key] == value

    @pytest.mark.anyio
    async def test_answer_overrides(self):
        """answer_overrides merge with and override defaults."""
        engine = _make_mock_engine()
        overrides = {"depth": "5", "custom_key": "custom_value"}
        with patch(_ENGINE_PATCH, return_value=engine):
            await new_project_workflow(
                idea="test project", answer_overrides=overrides
            )
            call_kwargs = engine.run_gsd_command.call_args
            answer_map = call_kwargs.kwargs.get("answer_map")
            # Overridden value
            assert answer_map["depth"] == "5"
            # New key from overrides
            assert answer_map["custom_key"] == "custom_value"
            # Preserved defaults
            assert answer_map["parallelization"] == "Yes"

    def test_defaults_dict_has_expected_keys(self):
        """NEW_PROJECT_DEFAULTS has all expected config question keys."""
        expected_keys = {"depth", "parallelization", "git", "research", "plan check", "verif", "model"}
        assert set(NEW_PROJECT_DEFAULTS.keys()) == expected_keys


class TestNewProjectEngineConfig:
    @pytest.mark.anyio
    async def test_timeout_passed_to_engine(self):
        """Custom timeout is passed to the WorkflowEngine."""
        engine_cls = MagicMock(return_value=_make_mock_engine())
        with patch(_ENGINE_PATCH, engine_cls):
            await new_project_workflow(idea="test project", timeout=1200.0)
            init_kwargs = engine_cls.call_args
            assert init_kwargs.kwargs.get("timeout") == 1200.0

    @pytest.mark.anyio
    async def test_project_dir_propagation(self):
        """project_dir is passed to the WorkflowEngine."""
        engine_cls = MagicMock(return_value=_make_mock_engine())
        with patch(_ENGINE_PATCH, engine_cls):
            await new_project_workflow(
                idea="test project", project_dir="/custom/path"
            )
            init_kwargs = engine_cls.call_args
            assert init_kwargs.kwargs.get("project_dir") == "/custom/path"

    @pytest.mark.anyio
    async def test_verbose_propagation(self):
        """verbose flag is passed to the WorkflowEngine."""
        engine_cls = MagicMock(return_value=_make_mock_engine())
        with patch(_ENGINE_PATCH, engine_cls):
            await new_project_workflow(idea="test project", verbose=True)
            init_kwargs = engine_cls.call_args
            assert init_kwargs.kwargs.get("verbose") is True

    @pytest.mark.anyio
    async def test_quiet_propagation(self):
        """quiet flag is passed to the WorkflowEngine."""
        engine_cls = MagicMock(return_value=_make_mock_engine())
        with patch(_ENGINE_PATCH, engine_cls):
            await new_project_workflow(idea="test project", quiet=True)
            init_kwargs = engine_cls.call_args
            assert init_kwargs.kwargs.get("quiet") is True

    @pytest.mark.anyio
    async def test_default_project_dir_is_cwd(self):
        """When project_dir is None, os.getcwd() is used."""
        engine_cls = MagicMock(return_value=_make_mock_engine())
        with patch(_ENGINE_PATCH, engine_cls), patch(
            "openclawpack.commands.new_project.os.getcwd",
            return_value="/mocked/cwd",
        ):
            await new_project_workflow(idea="test project", project_dir=None)
            init_kwargs = engine_cls.call_args
            assert init_kwargs.kwargs.get("project_dir") == "/mocked/cwd"

    @pytest.mark.anyio
    async def test_gsd_command_is_new_project(self):
        """The engine receives 'gsd:new-project' as the command."""
        engine = _make_mock_engine()
        with patch(_ENGINE_PATCH, return_value=engine):
            await new_project_workflow(idea="test project")
            call_args = engine.run_gsd_command.call_args
            assert call_args[0][0] == "gsd:new-project"

    @pytest.mark.anyio
    async def test_returns_command_result(self):
        """The workflow returns a CommandResult from the engine."""
        engine = _make_mock_engine()
        with patch(_ENGINE_PATCH, return_value=engine):
            result = await new_project_workflow(idea="test project")
            assert isinstance(result, CommandResult)
            assert result.success is True


# ── Error handling tests ────────────────────────────────────────


class TestNewProjectErrorHandling:
    """new_project_workflow catches exceptions and returns structured errors."""

    @pytest.mark.anyio
    async def test_workflow_returns_error_on_failure(self):
        """Exception during workflow returns CommandResult.error(), not traceback."""
        engine = MagicMock()
        engine.run_gsd_command = AsyncMock(
            side_effect=Exception("Transport failed")
        )
        with patch(_ENGINE_PATCH, return_value=engine):
            result = await new_project_workflow(idea="test idea")

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Transport failed" in result.errors[0]
