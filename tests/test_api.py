"""Tests for the public library API (api.py).

Verifies that all seven async functions wrap their workflow counterparts,
accept event_bus, and emit the correct events on success/failure.

Patch targets use source module paths because api.py uses lazy imports
inside function bodies (PKG-04 pattern).
"""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openclawpack.events.bus import EventBus
from openclawpack.events.types import Event, EventType
from openclawpack.output.schema import CommandResult, ProjectStatus

# Patch targets at source modules (lazy imports in api.py function bodies)
_NEW_PROJECT_WF = "openclawpack.commands.new_project.new_project_workflow"
_PLAN_PHASE_WF = "openclawpack.commands.plan_phase.plan_phase_workflow"
_EXECUTE_PHASE_WF = "openclawpack.commands.execute_phase.execute_phase_workflow"
_STATUS_WF = "openclawpack.commands.status.status_workflow"


# ── Helpers ──────────────────────────────────────────────────────


def _ok_result(**kwargs) -> CommandResult:
    return CommandResult.ok(result={"status": "ok"}, duration_ms=1, **kwargs)


def _err_result(msg: str = "something broke") -> CommandResult:
    return CommandResult.error(msg)


def _status_dict() -> dict:
    return {
        "current_phase": 2,
        "current_phase_name": "Core Commands",
        "progress_percent": 50.0,
        "blockers": [],
        "requirements_complete": 4,
        "requirements_total": 8,
    }


# ── create_project ───────────────────────────────────────────────


class TestCreateProject:
    """Tests for api.create_project()."""

    def test_is_async_function(self) -> None:
        from openclawpack.api import create_project
        assert inspect.iscoroutinefunction(create_project)

    @pytest.mark.anyio
    async def test_calls_workflow_and_returns_result(self) -> None:
        from openclawpack.api import create_project

        ok = _ok_result()
        with patch(
            _NEW_PROJECT_WF,
            new_callable=AsyncMock,
            return_value=ok,
        ) as mock_wf:
            result = await create_project("build a todo app")
        mock_wf.assert_awaited_once()
        assert result.success is True

    @pytest.mark.anyio
    async def test_emits_progress_update_on_success(self) -> None:
        from openclawpack.api import create_project

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.PROGRESS_UPDATE, lambda e: captured.append(e))

        with patch(
            _NEW_PROJECT_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ):
            await create_project("build a todo app", event_bus=bus)

        assert len(captured) == 1
        assert captured[0].type == EventType.PROGRESS_UPDATE
        assert captured[0].data["command"] == "create_project"

    @pytest.mark.anyio
    async def test_emits_error_on_failure(self) -> None:
        from openclawpack.api import create_project

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.ERROR, lambda e: captured.append(e))

        with patch(
            _NEW_PROJECT_WF,
            new_callable=AsyncMock,
            return_value=_err_result(),
        ):
            await create_project("build a todo app", event_bus=bus)

        assert len(captured) == 1
        assert captured[0].type == EventType.ERROR
        assert captured[0].data["command"] == "create_project"

    @pytest.mark.anyio
    async def test_no_event_bus_does_not_crash(self) -> None:
        from openclawpack.api import create_project

        with patch(
            _NEW_PROJECT_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ):
            result = await create_project("build a todo app")
        assert result.success is True

    @pytest.mark.anyio
    async def test_emits_decision_needed_when_no_overrides(self) -> None:
        from openclawpack.api import create_project

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.DECISION_NEEDED, lambda e: captured.append(e))

        with patch(
            _NEW_PROJECT_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ):
            await create_project("build a todo app", event_bus=bus)

        assert len(captured) == 1
        assert captured[0].type == EventType.DECISION_NEEDED
        assert captured[0].data["command"] == "create_project"

    @pytest.mark.anyio
    async def test_no_decision_needed_when_overrides_provided(self) -> None:
        from openclawpack.api import create_project

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.DECISION_NEEDED, lambda e: captured.append(e))

        with patch(
            _NEW_PROJECT_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ):
            await create_project(
                "build a todo app",
                answer_overrides={"key": "val"},
                event_bus=bus,
            )

        assert len(captured) == 0

    def test_idea_is_required_parameter(self) -> None:
        from openclawpack.api import create_project

        sig = inspect.signature(create_project)
        params = list(sig.parameters.keys())
        assert params[0] == "idea"


# ── plan_phase ───────────────────────────────────────────────────


class TestPlanPhase:
    """Tests for api.plan_phase()."""

    def test_is_async_function(self) -> None:
        from openclawpack.api import plan_phase
        assert inspect.iscoroutinefunction(plan_phase)

    @pytest.mark.anyio
    async def test_calls_workflow_and_returns_result(self) -> None:
        from openclawpack.api import plan_phase

        with patch(
            _PLAN_PHASE_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ) as mock_wf:
            result = await plan_phase(1)
        mock_wf.assert_awaited_once()
        assert result.success is True

    @pytest.mark.anyio
    async def test_emits_plan_complete_on_success(self) -> None:
        from openclawpack.api import plan_phase

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.PLAN_COMPLETE, lambda e: captured.append(e))

        with patch(
            _PLAN_PHASE_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ):
            await plan_phase(2, event_bus=bus)

        assert len(captured) == 1
        assert captured[0].data["command"] == "plan_phase"
        assert captured[0].data["phase"] == 2

    @pytest.mark.anyio
    async def test_emits_error_on_failure(self) -> None:
        from openclawpack.api import plan_phase

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.ERROR, lambda e: captured.append(e))

        with patch(
            _PLAN_PHASE_WF,
            new_callable=AsyncMock,
            return_value=_err_result(),
        ):
            await plan_phase(1, event_bus=bus)

        assert len(captured) == 1
        assert captured[0].type == EventType.ERROR

    @pytest.mark.anyio
    async def test_emits_decision_needed_when_no_overrides(self) -> None:
        from openclawpack.api import plan_phase

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.DECISION_NEEDED, lambda e: captured.append(e))

        with patch(
            _PLAN_PHASE_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ):
            await plan_phase(1, event_bus=bus)

        assert len(captured) == 1
        assert captured[0].type == EventType.DECISION_NEEDED
        assert captured[0].data["command"] == "plan_phase"

    @pytest.mark.anyio
    async def test_no_decision_needed_when_overrides_provided(self) -> None:
        from openclawpack.api import plan_phase

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.DECISION_NEEDED, lambda e: captured.append(e))

        with patch(
            _PLAN_PHASE_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ):
            await plan_phase(1, answer_overrides={"key": "val"}, event_bus=bus)

        assert len(captured) == 0


# ── execute_phase ────────────────────────────────────────────────


class TestExecutePhase:
    """Tests for api.execute_phase()."""

    def test_is_async_function(self) -> None:
        from openclawpack.api import execute_phase
        assert inspect.iscoroutinefunction(execute_phase)

    @pytest.mark.anyio
    async def test_calls_workflow_and_returns_result(self) -> None:
        from openclawpack.api import execute_phase

        with patch(
            _EXECUTE_PHASE_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ) as mock_wf:
            result = await execute_phase(1)
        mock_wf.assert_awaited_once()
        assert result.success is True

    @pytest.mark.anyio
    async def test_emits_phase_complete_on_success(self) -> None:
        from openclawpack.api import execute_phase

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.PHASE_COMPLETE, lambda e: captured.append(e))

        with patch(
            _EXECUTE_PHASE_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ):
            await execute_phase(3, event_bus=bus)

        assert len(captured) == 1
        assert captured[0].data["command"] == "execute_phase"
        assert captured[0].data["phase"] == 3

    @pytest.mark.anyio
    async def test_emits_error_on_failure(self) -> None:
        from openclawpack.api import execute_phase

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.ERROR, lambda e: captured.append(e))

        with patch(
            _EXECUTE_PHASE_WF,
            new_callable=AsyncMock,
            return_value=_err_result(),
        ):
            await execute_phase(1, event_bus=bus)

        assert len(captured) == 1
        assert captured[0].type == EventType.ERROR

    @pytest.mark.anyio
    async def test_emits_decision_needed_when_no_overrides(self) -> None:
        from openclawpack.api import execute_phase

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.DECISION_NEEDED, lambda e: captured.append(e))

        with patch(
            _EXECUTE_PHASE_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ):
            await execute_phase(1, event_bus=bus)

        assert len(captured) == 1
        assert captured[0].type == EventType.DECISION_NEEDED
        assert captured[0].data["command"] == "execute_phase"

    @pytest.mark.anyio
    async def test_no_decision_needed_when_overrides_provided(self) -> None:
        from openclawpack.api import execute_phase

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.DECISION_NEEDED, lambda e: captured.append(e))

        with patch(
            _EXECUTE_PHASE_WF,
            new_callable=AsyncMock,
            return_value=_ok_result(),
        ):
            await execute_phase(
                1, answer_overrides={"key": "val"}, event_bus=bus,
            )

        assert len(captured) == 0


# ── get_status ───────────────────────────────────────────────────


class TestGetStatus:
    """Tests for api.get_status()."""

    def test_is_async_function(self) -> None:
        from openclawpack.api import get_status
        assert inspect.iscoroutinefunction(get_status)

    @pytest.mark.anyio
    async def test_calls_workflow_and_returns_result(self) -> None:
        from openclawpack.api import get_status

        ok = CommandResult.ok(result=_status_dict(), duration_ms=5)
        with patch(_STATUS_WF, return_value=ok) as mock_wf:
            result = await get_status()
        mock_wf.assert_called_once()
        assert result.success is True

    @pytest.mark.anyio
    async def test_converts_dict_to_project_status(self) -> None:
        from openclawpack.api import get_status

        ok = CommandResult.ok(result=_status_dict(), duration_ms=5)
        with patch(_STATUS_WF, return_value=ok):
            result = await get_status()

        assert isinstance(result.result, ProjectStatus)
        assert result.result.current_phase == 2
        assert result.result.current_phase_name == "Core Commands"

    @pytest.mark.anyio
    async def test_non_dict_result_passes_through(self) -> None:
        from openclawpack.api import get_status

        ok = CommandResult.ok(result="some string", duration_ms=5)
        with patch(_STATUS_WF, return_value=ok):
            result = await get_status()

        assert result.result == "some string"

    @pytest.mark.anyio
    async def test_emits_progress_update_on_success(self) -> None:
        from openclawpack.api import get_status

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.PROGRESS_UPDATE, lambda e: captured.append(e))

        ok = CommandResult.ok(result=_status_dict(), duration_ms=5)
        with patch(_STATUS_WF, return_value=ok):
            await get_status(event_bus=bus)

        assert len(captured) == 1
        assert captured[0].data["command"] == "get_status"


# ── add_project ─────────────────────────────────────────────────


_REGISTRY = "openclawpack.state.registry.ProjectRegistry"


class TestAddProject:
    """Tests for api.add_project()."""

    def test_is_async_function(self) -> None:
        from openclawpack.api import add_project

        assert inspect.iscoroutinefunction(add_project)

    @pytest.mark.anyio
    async def test_add_project_success(self) -> None:
        from openclawpack.api import add_project

        mock_entry = MagicMock()
        mock_entry.model_dump.return_value = {
            "name": "myproject",
            "path": "/tmp/myproject",
            "registered_at": "2026-01-01T00:00:00Z",
        }
        mock_registry = MagicMock()
        mock_registry.add.return_value = mock_entry

        with patch(
            _REGISTRY,
        ) as mock_cls:
            mock_cls.load.return_value = mock_registry
            result = await add_project("/tmp/myproject")

        assert result.success is True
        assert result.result["name"] == "myproject"

    @pytest.mark.anyio
    async def test_add_project_invalid_path(self) -> None:
        from openclawpack.api import add_project

        mock_registry = MagicMock()
        mock_registry.add.side_effect = ValueError("Path does not exist")

        with patch(_REGISTRY) as mock_cls:
            mock_cls.load.return_value = mock_registry
            result = await add_project("/nonexistent")

        assert result.success is False
        assert "does not exist" in result.errors[0]

    @pytest.mark.anyio
    async def test_add_project_emits_event(self) -> None:
        from openclawpack.api import add_project

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.PROGRESS_UPDATE, lambda e: captured.append(e))
        bus.on(EventType.ERROR, lambda e: captured.append(e))

        mock_entry = MagicMock()
        mock_entry.model_dump.return_value = {"name": "proj"}
        mock_entry.name = "proj"
        mock_registry = MagicMock()
        mock_registry.add.return_value = mock_entry

        with patch(_REGISTRY) as mock_cls:
            mock_cls.load.return_value = mock_registry
            await add_project("/tmp/proj", event_bus=bus)

        assert len(captured) == 1
        assert captured[0].type == EventType.PROGRESS_UPDATE
        assert captured[0].data["command"] == "add_project"

    @pytest.mark.anyio
    async def test_add_project_error_emits_event(self) -> None:
        from openclawpack.api import add_project

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.ERROR, lambda e: captured.append(e))

        mock_registry = MagicMock()
        mock_registry.add.side_effect = ValueError("bad path")

        with patch(_REGISTRY) as mock_cls:
            mock_cls.load.return_value = mock_registry
            await add_project("/bad", event_bus=bus)

        assert len(captured) == 1
        assert captured[0].type == EventType.ERROR
        assert captured[0].data["command"] == "add_project"


# ── list_projects ───────────────────────────────────────────────


class TestListProjects:
    """Tests for api.list_projects()."""

    def test_is_async_function(self) -> None:
        from openclawpack.api import list_projects

        assert inspect.iscoroutinefunction(list_projects)

    @pytest.mark.anyio
    async def test_list_projects_success(self) -> None:
        from openclawpack.api import list_projects

        mock_entry = MagicMock()
        mock_entry.model_dump.return_value = {
            "name": "proj1",
            "path": "/tmp/proj1",
        }
        mock_registry = MagicMock()
        mock_registry.list_projects.return_value = [mock_entry]

        with patch(_REGISTRY) as mock_cls:
            mock_cls.load.return_value = mock_registry
            result = await list_projects()

        assert result.success is True
        assert len(result.result) == 1
        assert result.result[0]["name"] == "proj1"

    @pytest.mark.anyio
    async def test_list_projects_empty(self) -> None:
        from openclawpack.api import list_projects

        mock_registry = MagicMock()
        mock_registry.list_projects.return_value = []

        with patch(_REGISTRY) as mock_cls:
            mock_cls.load.return_value = mock_registry
            result = await list_projects()

        assert result.success is True
        assert result.result == []

    @pytest.mark.anyio
    async def test_list_projects_emits_event(self) -> None:
        from openclawpack.api import list_projects

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.PROGRESS_UPDATE, lambda e: captured.append(e))

        mock_registry = MagicMock()
        mock_registry.list_projects.return_value = []

        with patch(_REGISTRY) as mock_cls:
            mock_cls.load.return_value = mock_registry
            await list_projects(event_bus=bus)

        assert len(captured) == 1
        assert captured[0].data["command"] == "list_projects"


# ── remove_project ──────────────────────────────────────────────


class TestRemoveProject:
    """Tests for api.remove_project()."""

    def test_is_async_function(self) -> None:
        from openclawpack.api import remove_project

        assert inspect.iscoroutinefunction(remove_project)

    @pytest.mark.anyio
    async def test_remove_project_success(self) -> None:
        from openclawpack.api import remove_project

        mock_registry = MagicMock()
        mock_registry.remove.return_value = True

        with patch(_REGISTRY) as mock_cls:
            mock_cls.load.return_value = mock_registry
            result = await remove_project("myproject")

        assert result.success is True
        assert result.result["removed"] == "myproject"

    @pytest.mark.anyio
    async def test_remove_project_not_found(self) -> None:
        from openclawpack.api import remove_project

        mock_registry = MagicMock()
        mock_registry.remove.return_value = False

        with patch(_REGISTRY) as mock_cls:
            mock_cls.load.return_value = mock_registry
            result = await remove_project("nonexistent")

        assert result.success is False
        assert "not found" in result.errors[0]

    @pytest.mark.anyio
    async def test_remove_project_emits_event(self) -> None:
        from openclawpack.api import remove_project

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.PROGRESS_UPDATE, lambda e: captured.append(e))

        mock_registry = MagicMock()
        mock_registry.remove.return_value = True

        with patch(_REGISTRY) as mock_cls:
            mock_cls.load.return_value = mock_registry
            await remove_project("proj", event_bus=bus)

        assert len(captured) == 1
        assert captured[0].data["command"] == "remove_project"

    @pytest.mark.anyio
    async def test_remove_project_error_emits_event(self) -> None:
        from openclawpack.api import remove_project

        bus = EventBus()
        captured: list[Event] = []
        bus.on(EventType.ERROR, lambda e: captured.append(e))

        mock_registry = MagicMock()
        mock_registry.remove.side_effect = Exception("disk error")

        with patch(_REGISTRY) as mock_cls:
            mock_cls.load.return_value = mock_registry
            await remove_project("proj", event_bus=bus)

        assert len(captured) == 1
        assert captured[0].type == EventType.ERROR


# ── Package imports ─────────────────────────────────────────────


class TestPackageImportsAPI:
    """Tests for new API function imports from top-level package."""

    def test_import_add_project(self) -> None:
        from openclawpack import add_project

        assert inspect.iscoroutinefunction(add_project)

    def test_import_list_projects(self) -> None:
        from openclawpack import list_projects

        assert inspect.iscoroutinefunction(list_projects)

    def test_import_remove_project(self) -> None:
        from openclawpack import remove_project

        assert inspect.iscoroutinefunction(remove_project)
