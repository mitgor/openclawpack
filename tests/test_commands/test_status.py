"""Tests for the status command workflow."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from openclawpack.commands.status import status_workflow


# ── Fixtures ─────────────────────────────────────────────────────


def _create_minimal_planning(tmpdir: str) -> None:
    """Create a minimal .planning/ directory with required files."""
    planning = Path(tmpdir) / ".planning"
    planning.mkdir()

    (planning / "STATE.md").write_text(
        """\
# Project State

## Current Position

Phase: 1 of 2 (Foundation)
Plan: 1 of 3 in current phase
Status: Executing
""",
        encoding="utf-8",
    )

    (planning / "PROJECT.md").write_text(
        """\
# TestProject

## What This Is

A test project for status workflow.

## Core Value

Testing status output.
""",
        encoding="utf-8",
    )


# ── Tests ────────────────────────────────────────────────────────


class TestStatusWorkflow:
    def test_status_returns_project_summary(self):
        """status_workflow on a valid .planning/ dir returns success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_minimal_planning(tmpdir)
            result = status_workflow(project_dir=tmpdir)
            assert result.success is True
            assert result.result is not None
            assert isinstance(result.result, dict)
            assert "current_phase" in result.result

    def test_status_missing_planning_dir(self):
        """status_workflow with no .planning/ returns error result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = status_workflow(project_dir=tmpdir)
            assert result.success is False
            assert len(result.errors) > 0
            assert "planning" in result.errors[0].lower()

    def test_status_default_project_dir(self):
        """status_workflow defaults to cwd when project_dir is None."""
        with patch("openclawpack.commands.status.os.getcwd", return_value="/fake/path"):
            # /fake/path won't have .planning/ so we expect an error
            result = status_workflow(project_dir=None)
            assert result.success is False

    def test_status_duration_tracked(self):
        """duration_ms should be > 0 (or at least >= 0) in the result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_minimal_planning(tmpdir)
            result = status_workflow(project_dir=tmpdir)
            assert result.duration_ms >= 0

    def test_status_result_has_all_fields(self):
        """The result dict must contain all expected keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_minimal_planning(tmpdir)
            result = status_workflow(project_dir=tmpdir)
            assert result.success is True
            expected_keys = {
                "current_phase",
                "current_phase_name",
                "progress_percent",
                "blockers",
                "requirements_complete",
                "requirements_total",
            }
            assert expected_keys.issubset(result.result.keys())

    def test_status_error_has_duration(self):
        """Error results should also track duration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = status_workflow(project_dir=tmpdir)
            assert result.success is False
            assert result.duration_ms >= 0

    def test_status_on_real_project(self):
        """status_workflow('.') works on this repo (which has .planning/)."""
        result = status_workflow(project_dir=".")
        assert result.success is True
        assert result.result["current_phase"] >= 1
        assert result.result["requirements_total"] > 0
