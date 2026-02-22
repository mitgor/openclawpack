"""Status command workflow -- local-only project state reader.

Reads the .planning/ directory and returns a structured summary
wrapped in a :class:`CommandResult` envelope. No subprocess needed.
"""

from __future__ import annotations

import os

from openclawpack.output.schema import CommandResult


def status_workflow(project_dir: str | None = None) -> CommandResult:
    """Return structured project state as a CommandResult.

    Args:
        project_dir: Path to the project root directory (containing
            ``.planning/``). Defaults to the current working directory.

    Returns:
        A :class:`CommandResult` with the project summary dict on success,
        or an error message when ``.planning/`` is missing.
    """
    import time

    from openclawpack.state.reader import get_project_summary

    start = time.monotonic()
    target = project_dir if project_dir is not None else os.getcwd()

    try:
        summary = get_project_summary(target)
        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult.ok(result=summary, duration_ms=duration_ms)
    except FileNotFoundError as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult.error(str(e), duration_ms=duration_ms)
