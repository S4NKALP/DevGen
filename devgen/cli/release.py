import subprocess
from typing import Annotated

import typer

from devgen.modules.release_note_generator import ReleaseNotesGenerator

app = typer.Typer(
    name="release",
    help="🚀 Generate release notes from git history.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


@app.command("notes")
def generate_release_notes(
    version: Annotated[
        str,
        typer.Option("--version", "-v", help="Version for this release (ex: 1.4.0)"),
    ] = "Unreleased",
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output file path."),
    ] = "RELEASE-NOTES.md",
    from_ref: Annotated[
        str,
        typer.Option("--from", "-f", help="Start reference. Defaults to last tag."),
    ] = "",
) -> None:
    try:
        ReleaseNotesGenerator().run(
            output_file=output,
            version=version,
            from_ref=from_ref,
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        typer.secho(f"Error generating release notes: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
