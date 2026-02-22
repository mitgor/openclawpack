"""Tests for openclawpack.state.registry -- ProjectRegistry CRUD and persistence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from openclawpack.state.models import ProjectRegistryData, RegistryEntry


# ---------------------------------------------------------------------------
# RegistryEntry model
# ---------------------------------------------------------------------------


class TestRegistryEntry:
    """RegistryEntry Pydantic model round-trip tests."""

    def test_create_with_required_fields(self):
        entry = RegistryEntry(
            name="myproject",
            path="/home/user/myproject",
            registered_at="2026-02-22T12:00:00Z",
        )
        assert entry.name == "myproject"
        assert entry.path == "/home/user/myproject"
        assert entry.registered_at == "2026-02-22T12:00:00Z"
        assert entry.last_checked_at is None
        assert entry.last_known_state is None

    def test_create_with_all_fields(self):
        entry = RegistryEntry(
            name="myproject",
            path="/home/user/myproject",
            registered_at="2026-02-22T12:00:00Z",
            last_checked_at="2026-02-22T13:00:00Z",
            last_known_state={"current_phase": 3, "progress_percent": 50.0},
        )
        assert entry.last_checked_at == "2026-02-22T13:00:00Z"
        assert entry.last_known_state == {
            "current_phase": 3,
            "progress_percent": 50.0,
        }

    def test_model_dump_round_trip(self):
        entry = RegistryEntry(
            name="myproject",
            path="/home/user/myproject",
            registered_at="2026-02-22T12:00:00Z",
            last_known_state={"phase": 1},
        )
        data = entry.model_dump()
        restored = RegistryEntry.model_validate(data)
        assert restored == entry


# ---------------------------------------------------------------------------
# ProjectRegistryData model
# ---------------------------------------------------------------------------


class TestProjectRegistryData:
    """ProjectRegistryData Pydantic model round-trip tests."""

    def test_defaults(self):
        data = ProjectRegistryData()
        assert data.version == 1
        assert data.projects == {}

    def test_with_entries(self):
        entry = RegistryEntry(
            name="proj1",
            path="/tmp/proj1",
            registered_at="2026-02-22T12:00:00Z",
        )
        data = ProjectRegistryData(projects={"proj1": entry})
        assert "proj1" in data.projects
        assert data.projects["proj1"].name == "proj1"

    def test_json_round_trip(self):
        entry = RegistryEntry(
            name="proj1",
            path="/tmp/proj1",
            registered_at="2026-02-22T12:00:00Z",
            last_known_state={"current_phase": 2},
        )
        data = ProjectRegistryData(projects={"proj1": entry})
        json_str = data.model_dump_json()
        restored = ProjectRegistryData.model_validate_json(json_str)
        assert restored == data
        assert restored.projects["proj1"].last_known_state == {"current_phase": 2}


# ---------------------------------------------------------------------------
# _user_data_dir
# ---------------------------------------------------------------------------


class TestUserDataDir:
    """Cross-platform user data directory resolution."""

    def test_returns_path(self):
        from openclawpack.state.registry import _user_data_dir

        result = _user_data_dir()
        assert isinstance(result, Path)

    def test_macos_path(self):
        from openclawpack.state.registry import _user_data_dir

        with patch.object(sys, "platform", "darwin"):
            result = _user_data_dir()
            assert "Library" in str(result)
            assert "Application Support" in str(result)
            assert str(result).endswith("openclawpack")

    def test_linux_default_path(self):
        from openclawpack.state.registry import _user_data_dir

        with patch.object(sys, "platform", "linux"), patch.dict(
            "os.environ", {}, clear=True
        ):
            result = _user_data_dir()
            assert ".local/share/openclawpack" in str(result)

    def test_linux_xdg_override(self):
        from openclawpack.state.registry import _user_data_dir

        with patch.object(sys, "platform", "linux"), patch.dict(
            "os.environ", {"XDG_DATA_HOME": "/custom/data"}, clear=True
        ):
            result = _user_data_dir()
            assert str(result) == "/custom/data/openclawpack"

    def test_windows_path(self):
        from openclawpack.state.registry import _user_data_dir

        with patch.object(sys, "platform", "win32"), patch.dict(
            "os.environ", {"LOCALAPPDATA": "C:\\Users\\test\\AppData\\Local"}
        ):
            result = _user_data_dir()
            assert "openclawpack" in str(result)


# ---------------------------------------------------------------------------
# ProjectRegistry.load
# ---------------------------------------------------------------------------


class TestProjectRegistryLoad:
    """Loading registry from file."""

    def test_load_nonexistent_file_returns_empty(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry = ProjectRegistry.load(tmp_path / "registry.json")
        assert registry.list_projects() == []

    def test_load_valid_json(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        entry_data = {
            "version": 1,
            "projects": {
                "proj1": {
                    "name": "proj1",
                    "path": "/tmp/proj1",
                    "registered_at": "2026-02-22T12:00:00Z",
                    "last_checked_at": None,
                    "last_known_state": None,
                }
            },
        }
        registry_file.write_text(json.dumps(entry_data), encoding="utf-8")
        registry = ProjectRegistry.load(registry_file)
        entries = registry.list_projects()
        assert len(entries) == 1
        assert entries[0].name == "proj1"

    def test_load_invalid_json_raises(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        registry_file.write_text("not valid json{{{", encoding="utf-8")
        with pytest.raises(ValueError, match="[Ii]nvalid|[Cc]orrupt|JSON"):
            ProjectRegistry.load(registry_file)


# ---------------------------------------------------------------------------
# ProjectRegistry.save
# ---------------------------------------------------------------------------


class TestProjectRegistrySave:
    """Saving registry to file."""

    def test_save_creates_valid_json(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        registry = ProjectRegistry.load(registry_file)
        registry.save()

        content = registry_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["version"] == 1
        assert data["projects"] == {}

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "subdir" / "deep" / "registry.json"
        registry = ProjectRegistry.load(registry_file)
        registry.save()

        assert registry_file.exists()
        data = json.loads(registry_file.read_text(encoding="utf-8"))
        assert data["version"] == 1

    def test_atomic_write_produces_correct_content(self, tmp_path: Path):
        """After save, file content matches expected registry data."""
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        registry = ProjectRegistry.load(registry_file)

        # Manually add entry to data for save testing
        entry = RegistryEntry(
            name="testproj",
            path="/tmp/testproj",
            registered_at="2026-02-22T12:00:00Z",
        )
        registry._data.projects["testproj"] = entry
        registry.save()

        content = registry_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert "testproj" in data["projects"]
        assert data["projects"]["testproj"]["path"] == "/tmp/testproj"


# ---------------------------------------------------------------------------
# ProjectRegistry.add
# ---------------------------------------------------------------------------


class TestProjectRegistryAdd:
    """Adding projects to registry."""

    def _make_gsd_project(self, base_path: Path, name: str = "myproject") -> Path:
        """Create a minimal GSD project directory structure."""
        project_dir = base_path / name
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / ".planning").mkdir(exist_ok=True)
        return project_dir

    def test_add_valid_project(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        project_dir = self._make_gsd_project(tmp_path)

        registry = ProjectRegistry.load(registry_file)
        with patch(
            "openclawpack.state.registry.get_project_summary",
            return_value={"current_phase": 1, "progress_percent": 0.0},
        ):
            entry = registry.add(project_dir)

        assert entry.name == "myproject"
        assert entry.path == str(project_dir.resolve())
        assert entry.last_known_state == {
            "current_phase": 1,
            "progress_percent": 0.0,
        }
        assert len(registry.list_projects()) == 1

    def test_add_auto_saves(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        project_dir = self._make_gsd_project(tmp_path)

        registry = ProjectRegistry.load(registry_file)
        with patch(
            "openclawpack.state.registry.get_project_summary",
            return_value={"current_phase": 1},
        ):
            registry.add(project_dir)

        # Verify file was written
        assert registry_file.exists()
        data = json.loads(registry_file.read_text(encoding="utf-8"))
        assert "myproject" in data["projects"]

    def test_add_with_custom_name(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        project_dir = self._make_gsd_project(tmp_path)

        registry = ProjectRegistry.load(registry_file)
        with patch(
            "openclawpack.state.registry.get_project_summary",
            return_value={"current_phase": 1},
        ):
            entry = registry.add(project_dir, name="custom-name")

        assert entry.name == "custom-name"
        assert len(registry.list_projects()) == 1

    def test_add_without_planning_dir_raises(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        project_dir = tmp_path / "no_planning"
        project_dir.mkdir()

        registry = ProjectRegistry.load(registry_file)
        with pytest.raises(ValueError, match=".planning"):
            registry.add(project_dir)

    def test_add_nonexistent_path_raises(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        registry = ProjectRegistry.load(registry_file)

        with pytest.raises(ValueError, match="[Dd]oes not exist|[Nn]ot found"):
            registry.add(tmp_path / "nonexistent")

    def test_add_duplicate_name_raises(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        project_dir1 = self._make_gsd_project(tmp_path, "proj1")
        project_dir2 = self._make_gsd_project(tmp_path, "proj2")

        registry = ProjectRegistry.load(registry_file)
        with patch(
            "openclawpack.state.registry.get_project_summary",
            return_value={"current_phase": 1},
        ):
            registry.add(project_dir1, name="samename")
            with pytest.raises(ValueError, match="[Aa]lready|[Dd]uplicate|[Ee]xists"):
                registry.add(project_dir2, name="samename")

    def test_add_duplicate_path_raises(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        project_dir = self._make_gsd_project(tmp_path)

        registry = ProjectRegistry.load(registry_file)
        with patch(
            "openclawpack.state.registry.get_project_summary",
            return_value={"current_phase": 1},
        ):
            registry.add(project_dir, name="name1")
            with pytest.raises(ValueError, match="[Aa]lready|[Dd]uplicate|[Pp]ath"):
                registry.add(project_dir, name="name2")

    def test_add_sets_iso_timestamp(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        project_dir = self._make_gsd_project(tmp_path)

        registry = ProjectRegistry.load(registry_file)
        with patch(
            "openclawpack.state.registry.get_project_summary",
            return_value={"current_phase": 1},
        ):
            entry = registry.add(project_dir)

        # Should be a valid ISO 8601 timestamp
        assert "T" in entry.registered_at
        assert len(entry.registered_at) > 10  # At least date + time


# ---------------------------------------------------------------------------
# ProjectRegistry.remove
# ---------------------------------------------------------------------------


class TestProjectRegistryRemove:
    """Removing projects from registry."""

    def _make_gsd_project(self, base_path: Path, name: str = "myproject") -> Path:
        project_dir = base_path / name
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / ".planning").mkdir(exist_ok=True)
        return project_dir

    def test_remove_existing_returns_true(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        project_dir = self._make_gsd_project(tmp_path)

        registry = ProjectRegistry.load(registry_file)
        with patch(
            "openclawpack.state.registry.get_project_summary",
            return_value={"current_phase": 1},
        ):
            registry.add(project_dir)

        result = registry.remove("myproject")
        assert result is True
        assert len(registry.list_projects()) == 0

    def test_remove_auto_saves(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        project_dir = self._make_gsd_project(tmp_path)

        registry = ProjectRegistry.load(registry_file)
        with patch(
            "openclawpack.state.registry.get_project_summary",
            return_value={"current_phase": 1},
        ):
            registry.add(project_dir)

        registry.remove("myproject")

        # Verify file was updated
        data = json.loads(registry_file.read_text(encoding="utf-8"))
        assert "myproject" not in data["projects"]

    def test_remove_nonexistent_returns_false(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        registry = ProjectRegistry.load(registry_file)

        result = registry.remove("does_not_exist")
        assert result is False


# ---------------------------------------------------------------------------
# ProjectRegistry.list_projects
# ---------------------------------------------------------------------------


class TestProjectRegistryListProjects:
    """Listing projects from registry."""

    def _make_gsd_project(self, base_path: Path, name: str = "myproject") -> Path:
        project_dir = base_path / name
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / ".planning").mkdir(exist_ok=True)
        return project_dir

    def test_empty_registry_returns_empty_list(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        registry = ProjectRegistry.load(registry_file)

        assert registry.list_projects() == []

    def test_returns_all_entries(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        proj1 = self._make_gsd_project(tmp_path, "proj1")
        proj2 = self._make_gsd_project(tmp_path, "proj2")

        registry = ProjectRegistry.load(registry_file)
        with patch(
            "openclawpack.state.registry.get_project_summary",
            return_value={"current_phase": 1},
        ):
            registry.add(proj1)
            registry.add(proj2)

        entries = registry.list_projects()
        assert len(entries) == 2
        names = {e.name for e in entries}
        assert names == {"proj1", "proj2"}

    def test_returns_registry_entry_instances(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        proj1 = self._make_gsd_project(tmp_path, "proj1")

        registry = ProjectRegistry.load(registry_file)
        with patch(
            "openclawpack.state.registry.get_project_summary",
            return_value={"current_phase": 1},
        ):
            registry.add(proj1)

        entries = registry.list_projects()
        assert all(isinstance(e, RegistryEntry) for e in entries)


# ---------------------------------------------------------------------------
# Persistence round-trip
# ---------------------------------------------------------------------------


class TestPersistenceRoundTrip:
    """Full persistence: add, load from disk, verify."""

    def _make_gsd_project(self, base_path: Path, name: str = "myproject") -> Path:
        project_dir = base_path / name
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / ".planning").mkdir(exist_ok=True)
        return project_dir

    def test_add_then_reload(self, tmp_path: Path):
        from openclawpack.state.registry import ProjectRegistry

        registry_file = tmp_path / "registry.json"
        project_dir = self._make_gsd_project(tmp_path)

        # First registry: add project
        registry1 = ProjectRegistry.load(registry_file)
        with patch(
            "openclawpack.state.registry.get_project_summary",
            return_value={"current_phase": 2, "progress_percent": 33.3},
        ):
            registry1.add(project_dir)

        # Second registry: load from same file
        registry2 = ProjectRegistry.load(registry_file)
        entries = registry2.list_projects()
        assert len(entries) == 1
        assert entries[0].name == "myproject"
        assert entries[0].path == str(project_dir.resolve())
        assert entries[0].last_known_state == {
            "current_phase": 2,
            "progress_percent": 33.3,
        }
