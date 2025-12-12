import typer
from typing_extensions import Annotated

from devgen.modules.changelog_generator import ChangelogGenerator

app = typer.Typer(
    name="changelog",
    help="📝 Generate changelogs from git history.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


@app.command("generate")
def generate_changelog(
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Output file path.",
        ),
    ] = "CHANGELOG.md",
    from_ref: Annotated[
        str,
        typer.Option(
            "--from",
            "-f",
            help="Starting git reference (tag or hash). Defaults to last tag.",
        ),
    ] = "",
) -> None:
    generator = ChangelogGenerator()
    try:
        generator.run(output_file=output, from_ref=from_ref)
    except Exception as e:
        typer.secho(f"Error generating changelog: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
