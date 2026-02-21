"""OpenClawPack CLI entry point.

IMPORTANT: Do NOT import transport or state modules at module level.
--version and --help must work without Claude Code installed (PKG-04).
"""

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
) -> None:
    """OpenClawPack: Programmatic control over GSD via Claude Code."""


@app.command()
def status() -> None:
    """Show project state as structured JSON."""
    typer.echo('{"message": "not yet implemented"}')
