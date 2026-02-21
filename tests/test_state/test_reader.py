"""Integration tests for openclawpack.state.reader."""

import os
import tempfile
from pathlib import Path

import pytest

from openclawpack.state.reader import get_project_summary, read_project_state


class TestReadProjectState:
    """Integration tests using the real .planning/ directory."""

    def test_reads_real_project(self):
        """read_project_state('.') must return valid data from this repo."""
        pd = read_project_state(".")
        assert pd.state.current_phase >= 1
        assert pd.state.current_phase_name != "unknown"
        assert pd.project.name == "OpenClawPack"
        assert pd.project.description != "unknown"
        assert pd.project.core_value is not None

    def test_config_parsed(self):
        pd = read_project_state(".")
        assert pd.config.mode == "yolo"
        assert pd.config.parallelization is True

    def test_roadmap_has_phases(self):
        pd = read_project_state(".")
        assert len(pd.roadmap.phases) > 0
        assert pd.roadmap.overview is not None

    def test_requirements_parsed(self):
        pd = read_project_state(".")
        assert len(pd.requirements) > 0
        # Should have at least some completed requirements
        completed = [r for r in pd.requirements if r.completed]
        assert len(completed) > 0

    def test_current_phase_info(self):
        pd = read_project_state(".")
        assert pd.current_phase_info is not None
        assert pd.current_phase_info.number == pd.state.current_phase

    def test_overall_progress(self):
        pd = read_project_state(".")
        assert pd.overall_progress >= 0.0
        assert pd.overall_progress <= 100.0


class TestReadProjectStateMissingDir:
    def test_missing_planning_dir_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError, match="No .planning/ directory"):
                read_project_state(tmpdir)


class TestReadProjectStatePartial:
    def test_partial_planning_dir(self):
        """A .planning/ with only required files should return valid result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning = Path(tmpdir) / ".planning"
            planning.mkdir()

            # config.json
            (planning / "config.json").write_text(
                '{"mode": "yolo"}', encoding="utf-8"
            )

            # STATE.md (required)
            (planning / "STATE.md").write_text(
                """\
# Project State

## Current Position

Phase: 1 of 1 (Test)
Plan: 0 of 1 in current phase
Status: Starting
""",
                encoding="utf-8",
            )

            # PROJECT.md (required)
            (planning / "PROJECT.md").write_text(
                """\
# TestProject

## What This Is

A test project for partial state reading.

## Core Value

Testing graceful degradation.
""",
                encoding="utf-8",
            )

            pd = read_project_state(tmpdir)
            assert pd.state.current_phase == 1
            assert pd.project.name == "TestProject"
            # Optional files should have defaults
            assert pd.roadmap.phases == []
            assert pd.requirements == []

    def test_missing_state_md_raises(self):
        """STATE.md is required -- should raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning = Path(tmpdir) / ".planning"
            planning.mkdir()
            (planning / "PROJECT.md").write_text("# Test\n\n## What This Is\n\nTest.")
            with pytest.raises(FileNotFoundError, match="STATE.md"):
                read_project_state(tmpdir)

    def test_missing_project_md_raises(self):
        """PROJECT.md is required -- should raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning = Path(tmpdir) / ".planning"
            planning.mkdir()
            (planning / "STATE.md").write_text(
                "# Project State\n\n## Current Position\n\nPhase: 1 of 1 (Test)"
            )
            with pytest.raises(FileNotFoundError, match="PROJECT.md"):
                read_project_state(tmpdir)


class TestGetProjectSummary:
    def test_returns_expected_keys(self):
        summary = get_project_summary(".")
        assert "current_phase" in summary
        assert "current_phase_name" in summary
        assert "progress_percent" in summary
        assert "blockers" in summary
        assert "requirements_complete" in summary
        assert "requirements_total" in summary

    def test_values_are_correct_types(self):
        summary = get_project_summary(".")
        assert isinstance(summary["current_phase"], int)
        assert isinstance(summary["current_phase_name"], str)
        assert isinstance(summary["progress_percent"], float)
        assert isinstance(summary["blockers"], list)
        assert isinstance(summary["requirements_complete"], int)
        assert isinstance(summary["requirements_total"], int)

    def test_requirements_counts_consistent(self):
        summary = get_project_summary(".")
        assert summary["requirements_complete"] <= summary["requirements_total"]
        assert summary["requirements_total"] > 0
