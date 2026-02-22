"""Plan-phase workflow invoking GSD ``/gsd:plan-phase`` non-interactively.

Constructs the answer map for top-level GSD questions (CONTEXT.md creation,
confirmation prompts) and delegates to :class:`WorkflowEngine`.

Typical usage::

    result = await plan_phase_workflow(phase=2)
    print(result.to_json())
"""

from __future__ import annotations

from typing import Any

PLAN_PHASE_DEFAULTS: dict[str, str] = {
    "context": "Skip",     # Skip CONTEXT.md creation if missing
    "confirm": "Yes",      # Confirm plan breakdown
    "approve": "Yes",      # Approve generated plans
    "proceed": "Yes",      # Proceed with planning
}
"""Default answers for GSD plan-phase top-level questions.

Most plan-phase work happens in subagents (researchers, planners, checkers)
which run autonomously without AskUserQuestion. Only top-level confirmations
need answers.
"""


async def plan_phase_workflow(
    phase: int,
    project_dir: str | None = None,
    verbose: bool = False,
    quiet: bool = False,
    timeout: float | None = None,
    answer_overrides: dict[str, str] | None = None,
) -> Any:
    """Run ``/gsd:plan-phase <phase>`` non-interactively.

    Args:
        phase: Phase number to plan.
        project_dir: Working directory for the Claude subprocess.
            Defaults to ``os.getcwd()`` when *None*.
        verbose: Whether to show detailed subprocess output.
        quiet: Whether to suppress all non-JSON output.
        timeout: Timeout override in seconds.  Defaults to 600 s.
        answer_overrides: Extra answers merged on top of
            :data:`PLAN_PHASE_DEFAULTS`.

    Returns:
        A :class:`~openclawpack.output.schema.CommandResult` with the
        operation outcome.
    """
    # Lazy imports to preserve CLI independence (PKG-04)
    from openclawpack.commands.engine import WorkflowEngine

    answer_map = {**PLAN_PHASE_DEFAULTS, **(answer_overrides or {})}

    engine = WorkflowEngine(
        project_dir=project_dir,
        verbose=verbose,
        quiet=quiet,
        timeout=timeout or 600,
    )

    return await engine.run_gsd_command(
        "gsd:plan-phase",
        prompt_args=str(phase),
        answer_map=answer_map,
    )


def plan_phase_workflow_sync(
    phase: int,
    project_dir: str | None = None,
    verbose: bool = False,
    quiet: bool = False,
    timeout: float | None = None,
    answer_overrides: dict[str, str] | None = None,
) -> Any:
    """Synchronous wrapper for :func:`plan_phase_workflow`.

    Uses ``anyio.from_thread.run()`` to bridge sync-to-async.

    See :func:`plan_phase_workflow` for parameter documentation.
    """
    import anyio

    return anyio.from_thread.run(
        plan_phase_workflow,
        phase,
        project_dir,
        verbose,
        quiet,
        timeout,
        answer_overrides,
    )
