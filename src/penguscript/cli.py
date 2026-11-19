"""PenguScript command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from penguscript import __version__
from penguscript.analysis import analyze_project

app = typer.Typer(help="PenguScript compiler")


def version_callback(value: bool) -> None:
    """Print the compiler version and exit."""
    if value:
        typer.echo(f"PenguScript {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            help="Show compiler version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """PenguScript compiler."""


@app.command()
def check(
    path: Annotated[
        Path,
        typer.Argument(
            help="Path to project directory or .pengu source file",
            exists=True,
        ),
    ] = Path("."),
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Only display errors, suppress warnings",
        ),
    ] = False,
) -> None:
    """Analyze symbols, realms, and scopes without generating code."""
    annotated = analyze_project(path)

    sources: dict[Path, str] = {}
    num_errors = 0
    num_warnings = 0

    for diag in annotated.diagnostics:
        if diag.is_error:
            num_errors += 1
        elif diag.is_warning:
            num_warnings += 1

        if quiet and diag.is_warning:
            continue

        source_text: str | None = None
        if diag.source_file:
            src_path = Path(diag.source_file)
            if src_path.is_file():
                if src_path not in sources:
                    try:
                        sources[src_path] = src_path.read_text(encoding="utf-8")
                    except Exception:
                        sources[src_path] = ""
                source_text = sources[src_path]

        formatted = diag.format(
            source_text=source_text,
            filename=str(diag.source_file) if diag.source_file else None,
        )
        if diag.is_error:
            typer.secho(formatted, fg=typer.colors.RED)
        elif diag.is_warning:
            typer.secho(formatted, fg=typer.colors.YELLOW)
        else:
            typer.echo(formatted)

    if num_errors > 0:
        typer.secho(
            f"\nerror: check failed with {num_errors} error(s), {num_warnings} warning(s)",
            fg=typer.colors.RED,
            bold=True,
        )
        raise typer.Exit(code=1)

    if num_warnings > 0:
        typer.secho(
            f"\ncheck completed with {num_warnings} warning(s)",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=0)

    typer.secho("\ncheck passed: 0 errors, 0 warnings", fg=typer.colors.GREEN)
    raise typer.Exit(code=0)
