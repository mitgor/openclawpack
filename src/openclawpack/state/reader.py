"""High-level state reader orchestrating all parsers.

Reads a .planning/ directory and returns a fully typed
:class:`PlanningDirectory` model.
"""

from __future__ import annotations

from pathlib import Path

from openclawpack.state.models import (
    PlanningDirectory,
    ProjectConfig,
    RoadmapInfo,
)
from openclawpack.state.parser import (
    parse_config_json,
    parse_project_md,
    parse_requirements_md,
    parse_roadmap_md,
    parse_state_md,
)


def read_project_state(project_dir: str | Path) -> PlanningDirectory:
    """Read and parse all .planning/ files into a PlanningDirectory model.

    Args:
        project_dir: Path to the project root directory (containing .planning/).

    Returns:
        A :class:`PlanningDirectory` instance with all parsed state.

    Raises:
        FileNotFoundError: If the .planning/ directory does not exist, or if
            required files (STATE.md, PROJECT.md) are missing.
    """
    project_path = Path(project_dir).resolve()
    planning_dir = project_path / ".planning"

    if not planning_dir.is_dir():
        raise FileNotFoundError(
            f"No .planning/ directory found at {project_path}. "
            "Is this a GSD-managed project?"
        )

    # --- config.json (optional) ---
    config_path = planning_dir / "config.json"
    if config_path.is_file():
        config = parse_config_json(config_path.read_text(encoding="utf-8"))
    else:
        config = ProjectConfig()

    # --- STATE.md (required) ---
    state_path = planning_dir / "STATE.md"
    if not state_path.is_file():
        raise FileNotFoundError(
            f"Required file STATE.md not found in {planning_dir}. "
            "A GSD project must have a STATE.md file."
        )
    state = parse_state_md(state_path.read_text(encoding="utf-8"))

    # --- PROJECT.md (required) ---
    project_path_md = planning_dir / "PROJECT.md"
    if not project_path_md.is_file():
        raise FileNotFoundError(
            f"Required file PROJECT.md not found in {planning_dir}. "
            "A GSD project must have a PROJECT.md file."
        )
    project = parse_project_md(project_path_md.read_text(encoding="utf-8"))

    # --- ROADMAP.md (optional) ---
    roadmap_path = planning_dir / "ROADMAP.md"
    if roadmap_path.is_file():
        roadmap = parse_roadmap_md(roadmap_path.read_text(encoding="utf-8"))
    else:
        roadmap = RoadmapInfo()

    # --- REQUIREMENTS.md (optional) ---
    requirements_path = planning_dir / "REQUIREMENTS.md"
    if requirements_path.is_file():
        requirements = parse_requirements_md(
            requirements_path.read_text(encoding="utf-8")
        )
    else:
        requirements = []

    return PlanningDirectory(
        config=config,
        state=state,
        project=project,
        roadmap=roadmap,
        requirements=requirements,
    )


def get_project_summary(project_dir: str | Path) -> dict:
    """Return a convenience summary dict of the project state.

    This is what the ``status`` CLI command will use (wired in Phase 2).

    Args:
        project_dir: Path to the project root directory.

    Returns:
        A dict with keys: current_phase, current_phase_name,
        progress_percent, blockers, requirements_complete, requirements_total.
    """
    pd = read_project_state(project_dir)

    requirements_complete = sum(1 for r in pd.requirements if r.completed)
    requirements_total = len(pd.requirements)

    return {
        "current_phase": pd.state.current_phase,
        "current_phase_name": pd.state.current_phase_name,
        "progress_percent": pd.state.progress_percent,
        "blockers": pd.state.blockers,
        "requirements_complete": requirements_complete,
        "requirements_total": requirements_total,
    }
