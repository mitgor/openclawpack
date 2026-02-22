"""Persistent JSON registry of GSD projects.

Provides CRUD operations with atomic file persistence in a
cross-platform user data directory.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from openclawpack.state.models import ProjectRegistryData, RegistryEntry
from openclawpack.state.reader import get_project_summary


def _user_data_dir(appname: str = "openclawpack") -> Path:
    """Return platform-appropriate user data directory.

    - macOS: ~/Library/Application Support/<appname>
    - Linux: $XDG_DATA_HOME/<appname> or ~/.local/share/<appname>
    - Windows: %LOCALAPPDATA%/<appname>
    """
    if sys.platform == "win32":
        base = Path(
            os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        )
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux / other Unix
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / appname


def _atomic_write_json(path: Path, data: str) -> None:
    """Atomically write a JSON string to a file.

    Uses tempfile + os.replace to prevent corruption on crash.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class ProjectRegistry:
    """Manages a persistent JSON registry of GSD projects.

    Provides CRUD operations with atomic file persistence in a
    cross-platform user data directory.
    """

    def __init__(self, registry_path: Path, data: ProjectRegistryData) -> None:
        self._path = registry_path
        self._data = data

    @classmethod
    def load(cls, registry_path: Path | None = None) -> ProjectRegistry:
        """Load a registry from disk, or create an empty one.

        Args:
            registry_path: Path to the registry JSON file.
                If None, uses the default user data directory.

        Returns:
            A ProjectRegistry instance.

        Raises:
            ValueError: If the file exists but contains invalid JSON.
        """
        if registry_path is None:
            registry_path = _user_data_dir() / "registry.json"

        if not registry_path.exists():
            return cls(registry_path, ProjectRegistryData())

        content = registry_path.read_text(encoding="utf-8")
        try:
            data = ProjectRegistryData.model_validate_json(content)
        except Exception as exc:
            msg = f"Invalid or corrupt registry JSON at {registry_path}: {exc}"
            raise ValueError(msg) from exc

        return cls(registry_path, data)

    def save(self) -> None:
        """Persist the registry to disk using atomic write."""
        json_str = self._data.model_dump_json(indent=2)
        _atomic_write_json(self._path, json_str)

    def add(
        self, path: str | Path, *, name: str | None = None
    ) -> RegistryEntry:
        """Register a GSD project.

        Args:
            path: Path to the project root directory (must contain .planning/).
            name: Optional friendly name. Defaults to directory basename.

        Returns:
            The created RegistryEntry.

        Raises:
            ValueError: If path does not exist, has no .planning/ directory,
                or if the name or resolved path is already registered.
        """
        project_path = Path(path)

        # Validate path exists
        if not project_path.exists():
            raise ValueError(
                f"Path does not exist: {project_path}"
            )

        # Resolve to absolute canonical path
        resolved = project_path.resolve()

        # Validate .planning/ directory
        if not (resolved / ".planning").is_dir():
            raise ValueError(
                f"No .planning/ directory found at {resolved}. "
                "Is this a GSD-managed project?"
            )

        # Derive name
        entry_name = name if name is not None else resolved.name

        # Check duplicate name
        if entry_name in self._data.projects:
            raise ValueError(
                f"A project named '{entry_name}' already exists in the registry."
            )

        # Check duplicate path
        resolved_str = str(resolved)
        for existing in self._data.projects.values():
            if existing.path == resolved_str:
                raise ValueError(
                    f"Path '{resolved_str}' is already registered "
                    f"as '{existing.name}'."
                )

        # Snapshot state
        try:
            state_snapshot = get_project_summary(resolved)
        except Exception:
            state_snapshot = None

        # Create entry
        entry = RegistryEntry(
            name=entry_name,
            path=resolved_str,
            registered_at=datetime.now(timezone.utc).isoformat(),
            last_known_state=state_snapshot,
        )

        self._data.projects[entry_name] = entry
        self.save()
        return entry

    def remove(self, name: str) -> bool:
        """Remove a registered project by name.

        Args:
            name: The project name to remove.

        Returns:
            True if the project was removed, False if not found.
        """
        if name not in self._data.projects:
            return False

        del self._data.projects[name]
        self.save()
        return True

    def list_projects(self) -> list[RegistryEntry]:
        """Return all registered project entries.

        Returns:
            A list of RegistryEntry objects.
        """
        return list(self._data.projects.values())
