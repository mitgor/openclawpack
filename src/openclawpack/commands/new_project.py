"""New-project command workflow -- creates a GSD project non-interactively.

Constructs a ``/gsd:new-project --auto`` prompt with the project idea,
configures answer injection for GSD config questions, and invokes the
workflow engine to run the full new-project skill.
"""

from __future__ import annotations

import os
from pathlib import Path

from openclawpack.output.schema import CommandResult

# Default answers for GSD new-project config questions.
# Keys are substring patterns matched case-insensitively against question text.
NEW_PROJECT_DEFAULTS: dict[str, str] = {
    "depth": "3",
    "parallelization": "Yes",
    "git": "Yes",
    "research": "Standard",
    "plan check": "Yes",
    "verif": "Yes",
    "model": "quality",
}


async def new_project_workflow(
    idea: str,
    project_dir: str | None = None,
    verbose: bool = False,
    quiet: bool = False,
    timeout: float | None = None,
    answer_overrides: dict[str, str] | None = None,
) -> CommandResult:
    """Execute the new-project workflow via GSD.

    Args:
        idea: The project idea as plain text, or a file path whose
            contents will be read as the idea text.
        project_dir: Working directory for the Claude subprocess.
            Defaults to ``os.getcwd()`` when *None*.
        verbose: Whether to show detailed subprocess output.
        quiet: Whether to suppress all non-JSON output.
        timeout: Timeout in seconds; defaults to 900 for new-project.
        answer_overrides: Optional mapping to override default answers
            for GSD config questions. Merged on top of
            :data:`NEW_PROJECT_DEFAULTS`.

    Returns:
        A :class:`CommandResult` with the operation outcome.
    """
    try:
        # Lazy imports to avoid SDK dependency at module level (PKG-04)
        from openclawpack.commands.engine import WorkflowEngine

        # If idea looks like a file path, read its content
        idea_text = idea
        idea_path = Path(idea)
        if idea_path.is_file():
            idea_text = idea_path.read_text(encoding="utf-8")

        # Build answer map: defaults merged with overrides
        answer_map = {**NEW_PROJECT_DEFAULTS, **(answer_overrides or {})}

        # Construct prompt for GSD new-project skill
        prompt = f"/gsd:new-project --auto\n\n{idea_text}"

        # Create workflow engine
        engine = WorkflowEngine(
            project_dir=project_dir or os.getcwd(),
            verbose=verbose,
            quiet=quiet,
            timeout=timeout,
        )

        # Execute via engine with answer injection
        return await engine.run_gsd_command(
            "gsd:new-project",
            prompt_override=prompt,
            answer_map=answer_map,
        )
    except Exception as e:
        # Catch-all so CLI never shows raw tracebacks
        return CommandResult.error(str(e))


def new_project_workflow_sync(
    idea: str,
    project_dir: str | None = None,
    verbose: bool = False,
    quiet: bool = False,
    timeout: float | None = None,
    answer_overrides: dict[str, str] | None = None,
) -> CommandResult:
    """Synchronous wrapper for :func:`new_project_workflow`.

    Uses ``anyio.from_thread.run()`` to bridge sync-to-async.

    Args:
        idea: The project idea (text or file path).
        project_dir: Working directory for the Claude subprocess.
        verbose: Whether to show detailed subprocess output.
        quiet: Whether to suppress all non-JSON output.
        timeout: Timeout in seconds.
        answer_overrides: Optional answer overrides.

    Returns:
        A :class:`CommandResult` with the operation outcome.
    """
    import anyio

    return anyio.from_thread.run(
        new_project_workflow,
        idea,
        project_dir,
        verbose,
        quiet,
        timeout,
        answer_overrides,
    )
