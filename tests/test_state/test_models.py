"""Tests for Pydantic models in openclawpack.state.models."""

from openclawpack.state.models import (
    PhaseInfo,
    PlanningDirectory,
    ProjectConfig,
    ProjectInfo,
    ProjectState,
    RequirementInfo,
    RoadmapInfo,
)


class TestProjectConfig:
    def test_defaults(self):
        config = ProjectConfig()
        assert config.mode == "yolo"
        assert config.depth == "standard"
        assert config.parallelization is True
        assert config.commit_docs is True
        assert config.model_profile == "quality"

    def test_extra_fields_allowed(self):
        config = ProjectConfig(mode="careful", extra_field="hello")
        assert config.mode == "careful"
        assert config.extra_field == "hello"  # type: ignore[attr-defined]


class TestPhaseInfo:
    def test_minimal(self):
        phase = PhaseInfo(number=1, name="Foundation")
        assert phase.number == 1
        assert phase.name == "Foundation"
        assert phase.goal is None
        assert phase.requirements == []
        assert phase.plans_complete == 0
        assert phase.plans_total == 0
        assert phase.status == "Not started"

    def test_full(self):
        phase = PhaseInfo(
            number=2,
            name="Core Commands",
            goal="Build CLI commands",
            requirements=["CMD-01", "CMD-02"],
            plans_complete=1,
            plans_total=3,
            status="In Progress",
        )
        assert phase.goal == "Build CLI commands"
        assert len(phase.requirements) == 2


class TestRequirementInfo:
    def test_minimal(self):
        req = RequirementInfo(id="PKG-01", description="pip installable")
        assert req.id == "PKG-01"
        assert req.completed is False
        assert req.phase is None

    def test_completed(self):
        req = RequirementInfo(
            id="PKG-01", description="pip installable", phase=1, completed=True
        )
        assert req.completed is True
        assert req.phase == 1


class TestProjectState:
    def test_progress_percent_zero_plans(self):
        state = ProjectState(current_phase=1, current_phase_name="Foundation")
        assert state.progress_percent == 0.0

    def test_progress_percent_some_plans(self):
        state = ProjectState(
            current_phase=1,
            current_phase_name="Foundation",
            plans_complete=1,
            plans_total=3,
        )
        assert abs(state.progress_percent - 33.333333) < 0.01

    def test_progress_percent_all_plans(self):
        state = ProjectState(
            current_phase=1,
            current_phase_name="Foundation",
            plans_complete=3,
            plans_total=3,
        )
        assert state.progress_percent == 100.0

    def test_defaults(self):
        state = ProjectState(current_phase=1, current_phase_name="Foundation")
        assert state.blockers == []
        assert state.decisions == []
        assert state.last_activity is None


class TestProjectInfo:
    def test_minimal(self):
        info = ProjectInfo(name="TestProject", description="A test project")
        assert info.name == "TestProject"
        assert info.core_value is None
        assert info.constraints == []


class TestRoadmapInfo:
    def test_defaults(self):
        roadmap = RoadmapInfo()
        assert roadmap.phases == []
        assert roadmap.overview is None


class TestPlanningDirectory:
    def _make_directory(
        self,
        phase_count: int = 2,
        current_phase: int = 1,
        plans_per_phase: int = 3,
        plans_complete_per_phase: int = 1,
    ) -> PlanningDirectory:
        phases = [
            PhaseInfo(
                number=i + 1,
                name=f"Phase {i + 1}",
                plans_total=plans_per_phase,
                plans_complete=plans_complete_per_phase,
            )
            for i in range(phase_count)
        ]
        return PlanningDirectory(
            config=ProjectConfig(),
            state=ProjectState(
                current_phase=current_phase,
                current_phase_name=f"Phase {current_phase}",
            ),
            project=ProjectInfo(name="Test", description="Test project"),
            roadmap=RoadmapInfo(phases=phases),
        )

    def test_current_phase_info_found(self):
        pd = self._make_directory(current_phase=1)
        assert pd.current_phase_info is not None
        assert pd.current_phase_info.number == 1

    def test_current_phase_info_not_found(self):
        pd = self._make_directory(current_phase=99)
        assert pd.current_phase_info is None

    def test_overall_progress(self):
        # 2 phases, 3 plans each, 1 complete each => 2/6 = 33.33%
        pd = self._make_directory(
            phase_count=2,
            plans_per_phase=3,
            plans_complete_per_phase=1,
        )
        assert abs(pd.overall_progress - 33.333333) < 0.01

    def test_overall_progress_no_plans(self):
        pd = self._make_directory(
            phase_count=2,
            plans_per_phase=0,
            plans_complete_per_phase=0,
        )
        assert pd.overall_progress == 0.0

    def test_overall_progress_all_complete(self):
        pd = self._make_directory(
            phase_count=3,
            plans_per_phase=2,
            plans_complete_per_phase=2,
        )
        assert pd.overall_progress == 100.0
