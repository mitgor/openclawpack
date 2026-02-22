"""Public library API for openclawpack.

Exposes async functions that wrap internal workflow modules, adding
event bus integration and typed return values. Library consumers
use these functions directly instead of the CLI.

Usage::

    from openclawpack import create_project, plan_phase, execute_phase, get_status
    from openclawpack import add_project, list_projects, remove_project

    result = await create_project("build a todo app", event_bus=bus)
    status = await get_status(project_dir="/my/project")
    added = await add_project("/path/to/project", name="myapp")

All functions accept an optional ``event_bus`` parameter. When provided,
lifecycle events are emitted on success and failure. When omitted, a
default (no-op) EventBus is created internally.

IMPORTANT: Workflow imports are lazy (inside function bodies) to preserve
PKG-04 -- ``openclawpack --version`` must work without Claude Code installed.
"""

from __future__ import annotations

from openclawpack.events import EventBus, EventType
from openclawpack.output.schema import CommandResult


async def create_project(
    idea: str,
    *,
    project_dir: str | None = None,
    verbose: bool = False,
    quiet: bool = False,
    timeout: float | None = None,
    answer_overrides: dict[str, str] | None = None,
    resume_session_id: str | None = None,
    event_bus: EventBus | None = None,
) -> CommandResult:
    """Create a new GSD project from an idea.

    Wraps :func:`~openclawpack.commands.new_project.new_project_workflow`
    with event emission.

    Args:
        idea: The project idea as plain text.
        project_dir: Working directory for the Claude subprocess.
        verbose: Show detailed subprocess output.
        quiet: Suppress all non-JSON output.
        timeout: Timeout in seconds (defaults to 900).
        answer_overrides: Override default GSD config question answers.
        resume_session_id: Resume a previous Claude session.
        event_bus: Optional EventBus for lifecycle event emission.

    Returns:
        A CommandResult with the operation outcome.
    """
    # Lazy import to avoid SDK at module level (PKG-04)
    from openclawpack.commands.new_project import new_project_workflow

    bus = event_bus or EventBus()
    result = await new_project_workflow(
        idea=idea,
        project_dir=project_dir,
        verbose=verbose,
        quiet=quiet,
        timeout=timeout,
        answer_overrides=answer_overrides,
        resume_session_id=resume_session_id,
    )
    if result.success:
        await bus.emit_async(EventType.PROGRESS_UPDATE, {
            "command": "create_project",
            "status": "complete",
        })
    else:
        await bus.emit_async(EventType.ERROR, {
            "command": "create_project",
            "errors": result.errors,
        })
    return result


async def plan_phase(
    phase: int,
    *,
    project_dir: str | None = None,
    verbose: bool = False,
    quiet: bool = False,
    timeout: float | None = None,
    answer_overrides: dict[str, str] | None = None,
    resume_session_id: str | None = None,
    event_bus: EventBus | None = None,
) -> CommandResult:
    """Plan a GSD phase non-interactively.

    Wraps :func:`~openclawpack.commands.plan_phase.plan_phase_workflow`
    with event emission.

    Args:
        phase: Phase number to plan.
        project_dir: Working directory for the Claude subprocess.
        verbose: Show detailed subprocess output.
        quiet: Suppress all non-JSON output.
        timeout: Timeout in seconds (defaults to 600).
        answer_overrides: Override default GSD question answers.
        resume_session_id: Resume a previous Claude session.
        event_bus: Optional EventBus for lifecycle event emission.

    Returns:
        A CommandResult with the operation outcome.
    """
    # Lazy import to avoid SDK at module level (PKG-04)
    from openclawpack.commands.plan_phase import plan_phase_workflow

    bus = event_bus or EventBus()
    result = await plan_phase_workflow(
        phase=phase,
        project_dir=project_dir,
        verbose=verbose,
        quiet=quiet,
        timeout=timeout,
        answer_overrides=answer_overrides,
        resume_session_id=resume_session_id,
    )
    if result.success:
        await bus.emit_async(EventType.PLAN_COMPLETE, {
            "command": "plan_phase",
            "phase": phase,
        })
    else:
        await bus.emit_async(EventType.ERROR, {
            "command": "plan_phase",
            "phase": phase,
            "errors": result.errors,
        })
    return result


async def execute_phase(
    phase: int,
    *,
    project_dir: str | None = None,
    verbose: bool = False,
    quiet: bool = False,
    timeout: float | None = None,
    answer_overrides: dict[str, str] | None = None,
    resume_session_id: str | None = None,
    event_bus: EventBus | None = None,
) -> CommandResult:
    """Execute a GSD phase non-interactively.

    Wraps :func:`~openclawpack.commands.execute_phase.execute_phase_workflow`
    with event emission.

    Args:
        phase: Phase number to execute.
        project_dir: Working directory for the Claude subprocess.
        verbose: Show detailed subprocess output.
        quiet: Suppress all non-JSON output.
        timeout: Timeout in seconds (defaults to 1200).
        answer_overrides: Override default answer map.
        resume_session_id: Resume a previous Claude session.
        event_bus: Optional EventBus for lifecycle event emission.

    Returns:
        A CommandResult with the operation outcome.
    """
    # Lazy import to avoid SDK at module level (PKG-04)
    from openclawpack.commands.execute_phase import execute_phase_workflow

    bus = event_bus or EventBus()
    result = await execute_phase_workflow(
        phase=phase,
        project_dir=project_dir,
        verbose=verbose,
        quiet=quiet,
        timeout=timeout,
        answer_overrides=answer_overrides,
        resume_session_id=resume_session_id,
    )
    if result.success:
        await bus.emit_async(EventType.PHASE_COMPLETE, {
            "command": "execute_phase",
            "phase": phase,
        })
    else:
        await bus.emit_async(EventType.ERROR, {
            "command": "execute_phase",
            "phase": phase,
            "errors": result.errors,
        })
    return result


async def get_status(
    *,
    project_dir: str | None = None,
    event_bus: EventBus | None = None,
) -> CommandResult:
    """Get project status as a typed ProjectStatus model.

    Wraps :func:`~openclawpack.commands.status.status_workflow` (sync)
    and converts the raw dict result to a :class:`ProjectStatus` model
    when possible.

    Args:
        project_dir: Path to the project root directory.
        event_bus: Optional EventBus for lifecycle event emission.

    Returns:
        A CommandResult. On success, ``result`` is a :class:`ProjectStatus`
        instance if the dict conversion succeeds, otherwise the raw dict.
    """
    # Lazy imports to avoid SDK chain at module level (PKG-04)
    from openclawpack.commands.status import status_workflow
    from openclawpack.output.schema import ProjectStatus

    bus = event_bus or EventBus()
    result = status_workflow(project_dir=project_dir)

    # Convert raw dict to typed ProjectStatus model
    if result.success and isinstance(result.result, dict):
        try:
            status_model = ProjectStatus(**result.result)
            result = CommandResult.ok(
                result=status_model,
                session_id=result.session_id,
                usage=result.usage,
                duration_ms=result.duration_ms,
            )
        except Exception:
            pass  # Fall through with raw dict result

    if result.success:
        await bus.emit_async(EventType.PROGRESS_UPDATE, {
            "command": "get_status",
            "status": "complete",
        })
    else:
        await bus.emit_async(EventType.ERROR, {
            "command": "get_status",
            "errors": result.errors,
        })
    return result


async def add_project(
    path: str,
    *,
    name: str | None = None,
    event_bus: EventBus | None = None,
) -> CommandResult:
    """Register a GSD project in the multi-project registry.

    Args:
        path: Path to the project root directory (must contain .planning/).
        name: Optional friendly name. Defaults to directory basename.
        event_bus: Optional EventBus for lifecycle event emission.

    Returns:
        A CommandResult with the created RegistryEntry on success.
    """
    # Lazy import to preserve PKG-04
    from openclawpack.state.registry import ProjectRegistry

    bus = event_bus or EventBus()
    try:
        registry = ProjectRegistry.load()
        entry = registry.add(path, name=name)
        await bus.emit_async(EventType.PROGRESS_UPDATE, {
            "command": "add_project",
            "status": "complete",
            "project": entry.name,
        })
        return CommandResult.ok(result=entry.model_dump())
    except ValueError as exc:
        await bus.emit_async(EventType.ERROR, {
            "command": "add_project",
            "errors": [str(exc)],
        })
        return CommandResult.error(str(exc))
    except Exception as exc:
        await bus.emit_async(EventType.ERROR, {
            "command": "add_project",
            "errors": [str(exc)],
        })
        return CommandResult.error(str(exc))


async def list_projects(
    *,
    event_bus: EventBus | None = None,
) -> CommandResult:
    """List all registered GSD projects.

    Args:
        event_bus: Optional EventBus for lifecycle event emission.

    Returns:
        A CommandResult with a list of RegistryEntry dicts.
    """
    # Lazy import to preserve PKG-04
    from openclawpack.state.registry import ProjectRegistry

    bus = event_bus or EventBus()
    try:
        registry = ProjectRegistry.load()
        entries = [e.model_dump() for e in registry.list_projects()]
        await bus.emit_async(EventType.PROGRESS_UPDATE, {
            "command": "list_projects",
            "status": "complete",
            "count": len(entries),
        })
        return CommandResult.ok(result=entries)
    except Exception as exc:
        await bus.emit_async(EventType.ERROR, {
            "command": "list_projects",
            "errors": [str(exc)],
        })
        return CommandResult.error(str(exc))


async def remove_project(
    name: str,
    *,
    event_bus: EventBus | None = None,
) -> CommandResult:
    """Remove a project from the multi-project registry.

    Args:
        name: The project name to remove.
        event_bus: Optional EventBus for lifecycle event emission.

    Returns:
        A CommandResult indicating success or failure.
    """
    # Lazy import to preserve PKG-04
    from openclawpack.state.registry import ProjectRegistry

    bus = event_bus or EventBus()
    try:
        registry = ProjectRegistry.load()
        removed = registry.remove(name)
        if removed:
            await bus.emit_async(EventType.PROGRESS_UPDATE, {
                "command": "remove_project",
                "status": "complete",
                "project": name,
            })
            return CommandResult.ok(result={"removed": name})
        else:
            return CommandResult.error(
                f"Project '{name}' not found in registry."
            )
    except Exception as exc:
        await bus.emit_async(EventType.ERROR, {
            "command": "remove_project",
            "errors": [str(exc)],
        })
        return CommandResult.error(str(exc))
