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
    output_format: str = typer.Option(
        "json",
        "--output-format",
        help="Output format: json (default) or text.",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """OpenClawPack: Programmatic control over GSD via Claude Code."""
    ctx.ensure_object(dict)
    ctx.obj["project_dir"] = project_dir
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["output_format"] = output_format


# ── Output helper ────────────────────────────────────────────────


def _output(result: object, quiet: bool, output_format: str = "json") -> None:
    """Print a CommandResult to stdout (unless quiet).

    Args:
        result: A CommandResult instance.
        quiet: If True, suppress all output.
        output_format: Either "json" (default) or "text" for human-readable.
    """
    if quiet:
        return
    if output_format == "text":
        from openclawpack.output.formatter import format_text

        typer.echo(format_text(result))  # type: ignore[arg-type]
    else:
        typer.echo(result.to_json())  # type: ignore[union-attr]


# ── Event bus helper ────────────────────────────────────────────


def _make_cli_bus():
    """Create EventBus with CLI JSON-line handler for all event types.

    The returned bus writes ``event: {json}`` lines to stderr for each
    lifecycle event, enabling downstream tools to parse events alongside
    the primary JSON output on stdout.

    Uses lazy imports to preserve PKG-04 -- only called when a command
    runs, never at module import time.

    Returns:
        An :class:`EventBus` with :func:`cli_json_handler` registered
        on all five event types.
    """
    from openclawpack.events import EventBus, EventType
    from openclawpack.events.cli_handler import cli_json_handler

    bus = EventBus()
    for event_type in EventType:
        bus.on(event_type, cli_json_handler)
    return bus


# ── Shared option resolution ────────────────────────────────────


def _resolve_options(
    ctx: typer.Context,
    project_dir_opt: Optional[str],
    verbose_opt: bool,
    quiet_opt: bool,
) -> tuple[Optional[str], bool, bool]:
    """Resolve per-command options with fallback to global ctx.obj values."""
    project_dir = project_dir_opt or ctx.obj.get("project_dir")
    verbose = verbose_opt or ctx.obj.get("verbose", False)
    quiet = quiet_opt or ctx.obj.get("quiet", False)
    return project_dir, verbose, quiet


# ── Projects subcommand group ────────────────────────────────────
from openclawpack.commands.projects import projects_app

app.add_typer(projects_app, name="projects")


# ── Commands ─────────────────────────────────────────────────────


@app.command("new-project")
def new_project(
    idea: Optional[str] = typer.Argument(
        None, help="Project idea (text or brief description)."
    ),
    idea_opt: Optional[str] = typer.Option(
        None,
        "--idea",
        "-i",
        help="Project idea as a named option.",
    ),
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
    resume: Optional[str] = typer.Option(
        None,
        "--resume",
        help="Resume a previous Claude session by session ID.",
    ),
    project_dir_opt: Optional[str] = typer.Option(
        None,
        "--project-dir",
        help="Project directory (defaults to cwd).",
    ),
    verbose_opt: bool = typer.Option(
        False,
        "--verbose",
        help="Show detailed subprocess output.",
    ),
    quiet_opt: bool = typer.Option(
        False,
        "--quiet",
        help="Suppress all non-JSON output.",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """Create a new GSD project from an idea, non-interactively."""
    # Resolve idea text: --idea option takes precedence over positional arg
    idea_text: Optional[str] = None
    if idea_opt is not None:
        idea_text = idea_opt
    elif idea is not None:
        idea_text = idea

    # Read idea from file if --idea-file provided (overrides text)
    if idea_file is not None:
        idea_path = Path(idea_file)
        if not idea_path.is_file():
            typer.echo(f"Error: idea file not found: {idea_file}", err=True)
            raise typer.Exit(code=1)
        idea_text = idea_path.read_text(encoding="utf-8")

    if idea_text is None:
        typer.echo(
            "Error: Provide idea as positional argument or --idea option.",
            err=True,
        )
        raise typer.Exit(code=1)

    project_dir, verbose, quiet = _resolve_options(
        ctx, project_dir_opt, verbose_opt, quiet_opt
    )

    # Lazy import of API function (uses workflow internally)
    from openclawpack.api import create_project as create_project_api

    bus = _make_cli_bus() if not quiet else None
    result = asyncio.run(
        create_project_api(
            idea=idea_text,
            project_dir=project_dir,
            verbose=verbose,
            quiet=quiet,
            timeout=timeout,
            resume_session_id=resume,
            event_bus=bus,
        )
    )
    _output(result, quiet, ctx.obj.get("output_format", "json"))


@app.command("plan-phase")
def plan_phase(
    phase: int = typer.Argument(..., help="Phase number to plan."),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        help="Timeout in seconds (overrides default).",
    ),
    resume: Optional[str] = typer.Option(
        None,
        "--resume",
        help="Resume a previous Claude session by session ID.",
    ),
    project_dir_opt: Optional[str] = typer.Option(
        None,
        "--project-dir",
        help="Project directory (defaults to cwd).",
    ),
    verbose_opt: bool = typer.Option(
        False,
        "--verbose",
        help="Show detailed subprocess output.",
    ),
    quiet_opt: bool = typer.Option(
        False,
        "--quiet",
        help="Suppress all non-JSON output.",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """Plan a phase non-interactively."""
    project_dir, verbose, quiet = _resolve_options(
        ctx, project_dir_opt, verbose_opt, quiet_opt
    )

    # Lazy import of API function (uses workflow internally)
    from openclawpack.api import plan_phase as plan_phase_api

    bus = _make_cli_bus() if not quiet else None
    result = asyncio.run(
        plan_phase_api(
            phase=phase,
            project_dir=project_dir,
            verbose=verbose,
            quiet=quiet,
            timeout=timeout,
            resume_session_id=resume,
            event_bus=bus,
        )
    )
    _output(result, quiet, ctx.obj.get("output_format", "json"))


@app.command("execute-phase")
def execute_phase(
    phase: int = typer.Argument(..., help="Phase number to execute."),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        help="Timeout in seconds (overrides default).",
    ),
    resume: Optional[str] = typer.Option(
        None,
        "--resume",
        help="Resume a previous Claude session by session ID.",
    ),
    project_dir_opt: Optional[str] = typer.Option(
        None,
        "--project-dir",
        help="Project directory (defaults to cwd).",
    ),
    verbose_opt: bool = typer.Option(
        False,
        "--verbose",
        help="Show detailed subprocess output.",
    ),
    quiet_opt: bool = typer.Option(
        False,
        "--quiet",
        help="Suppress all non-JSON output.",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """Execute a phase non-interactively."""
    project_dir, verbose, quiet = _resolve_options(
        ctx, project_dir_opt, verbose_opt, quiet_opt
    )

    # Lazy import of API function (uses workflow internally)
    from openclawpack.api import execute_phase as execute_phase_api

    bus = _make_cli_bus() if not quiet else None
    result = asyncio.run(
        execute_phase_api(
            phase=phase,
            project_dir=project_dir,
            verbose=verbose,
            quiet=quiet,
            timeout=timeout,
            resume_session_id=resume,
            event_bus=bus,
        )
    )
    _output(result, quiet, ctx.obj.get("output_format", "json"))


@app.command()
def status(
    project_dir_opt: Optional[str] = typer.Option(
        None,
        "--project-dir",
        help="Project directory (defaults to cwd).",
    ),
    verbose_opt: bool = typer.Option(
        False,
        "--verbose",
        help="Show detailed subprocess output.",
    ),
    quiet_opt: bool = typer.Option(
        False,
        "--quiet",
        help="Suppress all non-JSON output.",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """Show project state as structured JSON."""
    project_dir, _verbose, quiet = _resolve_options(
        ctx, project_dir_opt, verbose_opt, quiet_opt
    )

    # Lazy import of workflow function
    from openclawpack.commands.status import status_workflow

    result = status_workflow(project_dir=project_dir)

    # Local-only commands: ensure usage is never None (Pitfall 4)
    if result.usage is None:
        result.usage = {"input_tokens": 0, "output_tokens": 0, "total_cost_usd": 0.0}

    _output(result, quiet, ctx.obj.get("output_format", "json"))
