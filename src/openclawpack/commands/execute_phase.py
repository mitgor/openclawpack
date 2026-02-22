"""Execute-phase workflow invoking GSD ``/gsd:execute-phase`` non-interactively.

Constructs the answer map for checkpoint approval, wave continuation, and
decision selection, then delegates to :class:`WorkflowEngine`.

Typical usage::

    result = await execute_phase_workflow(phase=2)
    print(result.to_json())
"""

from __future__ import annotations

from typing import Any

EXECUTE_PHASE_DEFAULTS: dict[str, str] = {
    "approve": "approved",     # Auto-approve checkpoints
    "approved": "approved",    # Alternative checkpoint wording
    "checkpoint": "approved",  # Checkpoint verification prompt
    "continue": "Yes",         # Continue to next wave
    "proceed": "Yes",          # Proceed with execution
    "select": "option-a",      # Select first option at decision checkpoints
}
"""Default answers for GSD execute-phase questions.

GSD ``--auto`` mode auto-approves checkpoints and selects first options.
The answer injection provides an additional safety layer for any prompts
that bypass auto mode.
"""


async def execute_phase_workflow(
    phase: int,
    project_dir: str | None = None,
    verbose: bool = False,
    quiet: bool = False,
    timeout: float | None = None,
    answer_overrides: dict[str, str] | None = None,
) -> Any:
    """Run ``/gsd:execute-phase <phase>`` non-interactively.

    Args:
        phase: Phase number to execute.
        project_dir: Working directory for the Claude subprocess.
            Defaults to ``os.getcwd()`` when *None*.
        verbose: Whether to show detailed subprocess output.
        quiet: Whether to suppress all non-JSON output.
        timeout: Timeout override in seconds.  Defaults to 1200 s
            (longer than other commands because execute-phase runs
            multiple subagents in waves).
        answer_overrides: Extra answers merged on top of
            :data:`EXECUTE_PHASE_DEFAULTS`.

    Returns:
        A :class:`~openclawpack.output.schema.CommandResult` with the
        operation outcome.
    """
    # Lazy imports to preserve CLI independence (PKG-04)
    from openclawpack.commands.engine import WorkflowEngine

    answer_map = {**EXECUTE_PHASE_DEFAULTS, **(answer_overrides or {})}

    engine = WorkflowEngine(
        project_dir=project_dir,
        verbose=verbose,
        quiet=quiet,
        timeout=timeout or 1200,
    )

    return await engine.run_gsd_command(
        "gsd:execute-phase",
        prompt_args=str(phase),
        answer_map=answer_map,
    )


def execute_phase_workflow_sync(
    phase: int,
    project_dir: str | None = None,
    verbose: bool = False,
    quiet: bool = False,
    timeout: float | None = None,
    answer_overrides: dict[str, str] | None = None,
) -> Any:
    """Synchronous wrapper for :func:`execute_phase_workflow`.

    Uses ``anyio.from_thread.run()`` to bridge sync-to-async.

    See :func:`execute_phase_workflow` for parameter documentation.
    """
    import anyio

    return anyio.from_thread.run(
        execute_phase_workflow,
        phase,
        project_dir,
        verbose,
        quiet,
        timeout,
        answer_overrides,
    )
