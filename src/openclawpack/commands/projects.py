"""CLI subcommand group for multi-project management.

Provides ``openclawpack projects add/list/remove`` commands that
delegate to :class:`~openclawpack.state.registry.ProjectRegistry`.

All heavy imports (ProjectRegistry, state parsers) are lazy --
importing ``projects_app`` only creates a Typer object, preserving
PKG-04 (``openclawpack --version`` works without Claude Code).
"""

from __future__ import annotations

from typing import Optional

import typer

from openclawpack.output.schema import CommandResult

projects_app = typer.Typer(help="Manage registered projects.")


def _output_result(
    result: CommandResult, ctx: typer.Context, quiet: bool
) -> None:
    """Print a CommandResult respecting quiet and output_format."""
    if quiet:
        return
    output_format = "json"
    if ctx.parent and ctx.parent.obj:
        output_format = ctx.parent.obj.get("output_format", "json")
    if output_format == "text":
        from openclawpack.output.formatter import format_text

        typer.echo(format_text(result))
    else:
        typer.echo(result.to_json())


@projects_app.command("add")
def add(
    path: str = typer.Argument(..., help="Path to a GSD project directory."),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Friendly name (defaults to directory basename).",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Suppress output.",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """Register a GSD project in the multi-project registry."""
    from openclawpack.state.registry import ProjectRegistry

    try:
        registry = ProjectRegistry.load()
        entry = registry.add(path, name=name)
        result = CommandResult.ok(result=entry.model_dump())
    except ValueError as exc:
        result = CommandResult.error(str(exc))
    except Exception as exc:
        result = CommandResult.error(str(exc))

    _output_result(result, ctx, quiet)


@projects_app.command("list")
def list_projects(
    refresh: bool = typer.Option(
        False,
        "--refresh",
        help="Re-read state from each project's .planning/ directory.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Suppress output.",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """List all registered projects."""
    from openclawpack.state.registry import ProjectRegistry

    try:
        registry = ProjectRegistry.load()
        entries = registry.list_projects()

        if refresh:
            from openclawpack.state.reader import get_project_summary
            from datetime import datetime, timezone

            for entry in entries:
                try:
                    summary = get_project_summary(entry.path)
                    entry.last_known_state = summary
                    entry.last_checked_at = datetime.now(
                        timezone.utc
                    ).isoformat()
                except Exception:
                    pass  # Leave existing state unchanged
            registry.save()

        result = CommandResult.ok(
            result=[e.model_dump() for e in entries]
        )
    except Exception as exc:
        result = CommandResult.error(str(exc))

    _output_result(result, ctx, quiet)


@projects_app.command("remove")
def remove(
    name: str = typer.Argument(..., help="Name of the project to remove."),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Suppress output.",
    ),
    ctx: typer.Context = typer.Context,
) -> None:
    """Remove a project from the registry."""
    from openclawpack.state.registry import ProjectRegistry

    try:
        registry = ProjectRegistry.load()
        removed = registry.remove(name)
        if removed:
            result = CommandResult.ok(result={"removed": name})
        else:
            result = CommandResult.error(
                f"Project '{name}' not found in registry."
            )
    except Exception as exc:
        result = CommandResult.error(str(exc))

    _output_result(result, ctx, quiet)
