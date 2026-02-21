"""Pydantic models for all .planning/ file types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, computed_field


class ProjectConfig(BaseModel):
    """Configuration from .planning/config.json."""

    model_config = ConfigDict(extra="allow")

    mode: str = "yolo"
    depth: str = "standard"
    parallelization: bool = True
    commit_docs: bool = True
    model_profile: str = "quality"


class PhaseInfo(BaseModel):
    """Information about a single phase from ROADMAP.md."""

    number: int
    name: str
    goal: str | None = None
    requirements: list[str] = []
    plans_complete: int = 0
    plans_total: int = 0
    status: str = "Not started"
    completed_date: str | None = None


class RequirementInfo(BaseModel):
    """A single requirement from REQUIREMENTS.md."""

    id: str
    description: str
    phase: int | None = None
    completed: bool = False


class ProjectState(BaseModel):
    """Parsed state from STATE.md."""

    current_phase: int
    current_phase_name: str
    plans_complete: int = 0
    plans_total: int = 0
    last_activity: str | None = None
    blockers: list[str] = []
    decisions: list[str] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def progress_percent(self) -> float:
        """Calculate progress as percentage of plans complete."""
        if self.plans_total > 0:
            return self.plans_complete / self.plans_total * 100
        return 0.0


class ProjectInfo(BaseModel):
    """Parsed project information from PROJECT.md."""

    name: str
    description: str
    core_value: str | None = None
    constraints: list[str] = []


class RoadmapInfo(BaseModel):
    """Parsed roadmap from ROADMAP.md."""

    phases: list[PhaseInfo] = []
    overview: str | None = None


class PlanningDirectory(BaseModel):
    """Complete parsed state of a .planning/ directory."""

    config: ProjectConfig
    state: ProjectState
    project: ProjectInfo
    roadmap: RoadmapInfo
    requirements: list[RequirementInfo] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def current_phase_info(self) -> PhaseInfo | None:
        """Return the PhaseInfo for the current phase, or None."""
        for phase in self.roadmap.phases:
            if phase.number == self.state.current_phase:
                return phase
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def overall_progress(self) -> float:
        """Calculate overall progress across all phases."""
        total_plans = sum(p.plans_total for p in self.roadmap.phases)
        complete_plans = sum(p.plans_complete for p in self.roadmap.phases)
        if total_plans > 0:
            return complete_plans / total_plans * 100
        return 0.0
