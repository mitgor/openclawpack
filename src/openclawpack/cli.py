"""OpenClawPack CLI entry point.

IMPORTANT: Do NOT import transport, state, or command modules at module level.
--version and --help must work without Claude Code installed (PKG-04).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="openclawpack",
    help="AI agent control over GSD framework via Claude Code",
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        from openclawpack._version import __version__

        typer.echo(f"openclawpack {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (defaults to cwd).",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Show detailed subprocess output.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all non-JSON output.",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """OpenClawPack: Programmatic control over GSD via Claude Code."""
    ctx.ensure_object(dict)
    ctx.obj["project_dir"] = project_dir
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


# ── Output helper ────────────────────────────────────────────────


def _output(result: object, quiet: bool) -> None:
    """Print a CommandResult as JSON to stdout (unless quiet)."""
    if not quiet:
        # result is a CommandResult with .to_json()
        typer.echo(result.to_json())  # type: ignore[union-attr]


# ── Commands ─────────────────────────────────────────────────────


@app.command("new-project")
def new_project(
    idea: str = typer.Argument(..., help="Project idea (text or brief description)."),
    idea_file: Optional[str] = typer.Option(
        None,
        "--idea-file",
        "-f",
        help="Path to file containing the project idea.",
    ),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        help="Timeout in seconds (overrides default).",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """Create a new GSD project from an idea, non-interactively."""
    # Read idea from file if --idea-file provided
    idea_text = idea
    if idea_file is not None:
        idea_path = Path(idea_file)
        if not idea_path.is_file():
            typer.echo(f"Error: idea file not found: {idea_file}", err=True)
            raise typer.Exit(code=1)
        idea_text = idea_path.read_text(encoding="utf-8")

    project_dir = ctx.obj.get("project_dir")
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)

    # Lazy import of workflow function
    from openclawpack.commands.new_project import new_project_workflow

    result = asyncio.run(
        new_project_workflow(
            idea=idea_text,
            project_dir=project_dir,
            verbose=verbose,
            quiet=quiet,
            timeout=timeout,
        )
    )
    _output(result, quiet)


@app.command("plan-phase")
def plan_phase(
    phase: int = typer.Argument(..., help="Phase number to plan."),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        help="Timeout in seconds (overrides default).",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """Plan a phase non-interactively."""
    project_dir = ctx.obj.get("project_dir")
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)

    # Lazy import of workflow function
    from openclawpack.commands.plan_phase import plan_phase_workflow

    result = asyncio.run(
        plan_phase_workflow(
            phase=phase,
            project_dir=project_dir,
            verbose=verbose,
            quiet=quiet,
            timeout=timeout,
        )
    )
    _output(result, quiet)


@app.command("execute-phase")
def execute_phase(
    phase: int = typer.Argument(..., help="Phase number to execute."),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        help="Timeout in seconds (overrides default).",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """Execute a phase non-interactively."""
    project_dir = ctx.obj.get("project_dir")
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)

    # Lazy import of workflow function
    from openclawpack.commands.execute_phase import execute_phase_workflow

    result = asyncio.run(
        execute_phase_workflow(
            phase=phase,
            project_dir=project_dir,
            verbose=verbose,
            quiet=quiet,
            timeout=timeout,
        )
    )
    _output(result, quiet)


@app.command()
def status(
    ctx: typer.Context = typer.Context,
) -> None:
    """Show project state as structured JSON."""
    import time

    project_dir = ctx.obj.get("project_dir")
    quiet = ctx.obj.get("quiet", False)

    start = time.monotonic()
    target = project_dir or "."

    try:
        # Lazy import of state reader
        from openclawpack.state.reader import get_project_summary

        from openclawpack.output.schema import CommandResult

        summary = get_project_summary(target)
        duration_ms = int((time.monotonic() - start) * 1000)
        result = CommandResult.ok(result=summary, duration_ms=duration_ms)
    except FileNotFoundError as e:
        from openclawpack.output.schema import CommandResult

        duration_ms = int((time.monotonic() - start) * 1000)
        result = CommandResult.error(str(e), duration_ms=duration_ms)

    _output(result, quiet)
