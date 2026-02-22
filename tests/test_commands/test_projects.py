"""Tests for projects CLI subcommand group (add, list, remove).

Verifies that ``openclawpack projects add/list/remove`` work end-to-end
using a temporary registry file and mock project directories.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from openclawpack.cli import app

runner = CliRunner()


# ── Helpers ──────────────────────────────────────────────────────


def _make_gsd_project(tmp_path: Path, name: str = "myproject") -> Path:
    """Create a minimal GSD project directory with .planning/."""
    project_dir = tmp_path / name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / ".planning").mkdir(exist_ok=True)
    # Minimal STATE.md for get_project_summary
    (project_dir / ".planning" / "STATE.md").write_text(
        "# Project State\n\n## Current Position\nPhase: 1 of 1 (Foundation)\n"
    )
    (project_dir / ".planning" / "PROJECT.md").write_text(
        "# Test Project\n\nDescription: test\n"
    )
    return project_dir


def _parse_output(result) -> dict:
    """Parse JSON output from CLI runner result."""
    return json.loads(result.output)


# ── Test Add ─────────────────────────────────────────────────────


class TestProjectsAdd:
    """Tests for ``openclawpack projects add``."""

    def test_add_success(self, tmp_path: Path) -> None:
        """Adding a valid GSD project directory registers it."""
        project_dir = _make_gsd_project(tmp_path)
        registry_path = tmp_path / "registry.json"

        with patch(
            "openclawpack.state.registry._user_data_dir",
            return_value=tmp_path,
        ):
            result = runner.invoke(
                app, ["projects", "add", str(project_dir)]
            )

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        data = _parse_output(result)
        assert data["success"] is True
        assert data["result"]["name"] == project_dir.name
        assert data["result"]["path"] == str(project_dir.resolve())

    def test_add_with_custom_name(self, tmp_path: Path) -> None:
        """Adding with --name uses the provided name."""
        project_dir = _make_gsd_project(tmp_path)

        with patch(
            "openclawpack.state.registry._user_data_dir",
            return_value=tmp_path,
        ):
            result = runner.invoke(
                app,
                ["projects", "add", str(project_dir), "--name", "custom"],
            )

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        data = _parse_output(result)
        assert data["success"] is True
        assert data["result"]["name"] == "custom"

    def test_add_nonexistent_path(self, tmp_path: Path) -> None:
        """Adding a nonexistent path returns an error."""
        with patch(
            "openclawpack.state.registry._user_data_dir",
            return_value=tmp_path,
        ):
            result = runner.invoke(
                app, ["projects", "add", str(tmp_path / "nope")]
            )

        assert result.exit_code == 0  # CLI exits 0, error in payload
        data = _parse_output(result)
        assert data["success"] is False
        assert "does not exist" in data["errors"][0]

    def test_add_path_without_planning(self, tmp_path: Path) -> None:
        """Adding a path without .planning/ returns an error."""
        bare_dir = tmp_path / "bare"
        bare_dir.mkdir()

        with patch(
            "openclawpack.state.registry._user_data_dir",
            return_value=tmp_path,
        ):
            result = runner.invoke(
                app, ["projects", "add", str(bare_dir)]
            )

        assert result.exit_code == 0
        data = _parse_output(result)
        assert data["success"] is False
        assert ".planning" in data["errors"][0]

    def test_add_duplicate_name(self, tmp_path: Path) -> None:
        """Adding a project with a name that already exists returns an error."""
        project_dir = _make_gsd_project(tmp_path, "proj1")
        project_dir2 = _make_gsd_project(tmp_path, "proj2")

        with patch(
            "openclawpack.state.registry._user_data_dir",
            return_value=tmp_path,
        ):
            # Add first
            runner.invoke(
                app,
                ["projects", "add", str(project_dir), "--name", "shared"],
            )
            # Add second with same name
            result = runner.invoke(
                app,
                ["projects", "add", str(project_dir2), "--name", "shared"],
            )

        data = _parse_output(result)
        assert data["success"] is False
        assert "already exists" in data["errors"][0]


# ── Test List ────────────────────────────────────────────────────


class TestProjectsList:
    """Tests for ``openclawpack projects list``."""

    def test_list_after_add(self, tmp_path: Path) -> None:
        """Listing after adding a project returns 1 entry."""
        project_dir = _make_gsd_project(tmp_path)

        with patch(
            "openclawpack.state.registry._user_data_dir",
            return_value=tmp_path,
        ):
            runner.invoke(app, ["projects", "add", str(project_dir)])
            result = runner.invoke(app, ["projects", "list"])

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        data = _parse_output(result)
        assert data["success"] is True
        assert len(data["result"]) == 1
        assert data["result"][0]["name"] == project_dir.name

    def test_list_empty_registry(self, tmp_path: Path) -> None:
        """Listing with no registered projects returns empty list."""
        with patch(
            "openclawpack.state.registry._user_data_dir",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["projects", "list"])

        assert result.exit_code == 0
        data = _parse_output(result)
        assert data["success"] is True
        assert data["result"] == []


# ── Test Remove ──────────────────────────────────────────────────


class TestProjectsRemove:
    """Tests for ``openclawpack projects remove``."""

    def test_remove_existing(self, tmp_path: Path) -> None:
        """Removing an existing project returns success."""
        project_dir = _make_gsd_project(tmp_path)

        with patch(
            "openclawpack.state.registry._user_data_dir",
            return_value=tmp_path,
        ):
            runner.invoke(app, ["projects", "add", str(project_dir)])
            result = runner.invoke(
                app, ["projects", "remove", project_dir.name]
            )

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        data = _parse_output(result)
        assert data["success"] is True
        assert data["result"]["removed"] == project_dir.name

    def test_remove_nonexistent(self, tmp_path: Path) -> None:
        """Removing a name that doesn't exist returns an error."""
        with patch(
            "openclawpack.state.registry._user_data_dir",
            return_value=tmp_path,
        ):
            result = runner.invoke(
                app, ["projects", "remove", "nonexistent"]
            )

        assert result.exit_code == 0
        data = _parse_output(result)
        assert data["success"] is False
        assert "not found" in data["errors"][0]

    def test_remove_then_list_empty(self, tmp_path: Path) -> None:
        """After removing the only project, list returns empty."""
        project_dir = _make_gsd_project(tmp_path)

        with patch(
            "openclawpack.state.registry._user_data_dir",
            return_value=tmp_path,
        ):
            runner.invoke(app, ["projects", "add", str(project_dir)])
            runner.invoke(
                app, ["projects", "remove", project_dir.name]
            )
            result = runner.invoke(app, ["projects", "list"])

        data = _parse_output(result)
        assert data["success"] is True
        assert data["result"] == []


# ── Test Quiet ───────────────────────────────────────────────────


class TestProjectsQuiet:
    """Tests for --quiet flag on projects commands."""

    def test_add_quiet(self, tmp_path: Path) -> None:
        """--quiet suppresses output on add."""
        project_dir = _make_gsd_project(tmp_path)

        with patch(
            "openclawpack.state.registry._user_data_dir",
            return_value=tmp_path,
        ):
            result = runner.invoke(
                app,
                ["projects", "add", str(project_dir), "--quiet"],
            )

        assert result.exit_code == 0
        assert result.output.strip() == ""
