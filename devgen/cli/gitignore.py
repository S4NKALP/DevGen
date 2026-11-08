from typing import Annotated

import questionary
import typer

from devgen.cli.wizard import ask
from devgen.modules.gitignore_generator import GitignoreGenerator
from devgen.utils import get_questionary_style

app = typer.Typer(
    name="gitignore",
    help="🙈 Generate .gitignore files from GitHub templates.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _select_templates(
    generator: GitignoreGenerator,
    offline: bool,
) -> list[str]:
    """Interactively build a list of templates to include."""
    if offline:
        available = generator.list_cached_templates()
    else:
        typer.secho("Fetching templates list...", fg=typer.colors.YELLOW)
        available = generator.list_available_templates()

    if not available:
        typer.secho(" No templates available.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    selected: list[str] = []
    style = get_questionary_style()

    while True:
        choices = [
            "Done (Finish selection)",
            *(name for name in available if name not in selected),
        ]
        choice = ask(
            questionary.autocomplete(
                "Search for a template (type to search, select 'Done' to finish):",
                choices=choices,
                ignore_case=True,
                match_middle=True,
                validate=lambda value, options=choices: value in options or value == "",
                style=style,
            )
        )

        if not choice or choice.startswith("Done"):
            return selected

        selected.append(choice)
        typer.secho(f"➕ Added '{choice}'", fg=typer.colors.GREEN)


@app.command("list")
def list_templates(
    cached: Annotated[
        bool,
        typer.Option("--cached", "-c", help="List only cached templates."),
    ] = False,
) -> None:
    """List available gitignore templates."""
    generator = GitignoreGenerator()
    try:
        if cached:
            templates = generator.list_cached_templates()
            typer.secho(" Cached Templates:", fg=typer.colors.CYAN, bold=True)
        else:
            typer.secho("Fetching available templates...", fg=typer.colors.YELLOW)
            templates = generator.list_available_templates()
            typer.secho(" Available Templates:", fg=typer.colors.CYAN, bold=True)
    except RuntimeError as error:
        typer.secho(f" Error: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(", ".join(templates) if templates else "No templates found.")


@app.command("generate")
def generate_gitignore(
    templates: Annotated[
        list[str] | None,
        typer.Argument(
            help="Names of templates to include (e.g. Python Node). "
            "If empty, interactive mode is used."
        ),
    ] = None,
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output file path."),
    ] = ".gitignore",
    append: Annotated[
        bool,
        typer.Option(
            "--append/--overwrite",
            "-a/-w",
            help="Append to existing file or overwrite.",
        ),
    ] = True,
    offline: Annotated[
        bool,
        typer.Option("--offline", help="Use only cached templates."),
    ] = False,
) -> None:
    """Generate a .gitignore file."""
    generator = GitignoreGenerator()

    if not templates:
        try:
            templates = _select_templates(generator, offline)
        except typer.Exit:
            raise
        except KeyboardInterrupt:
            typer.secho("\nCancelled by user", fg=typer.colors.YELLOW)
            raise typer.Exit()
        except (OSError, RuntimeError) as error:
            typer.secho(f"❌ Error fetching templates: {error}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        if not templates:
            typer.secho("No templates selected.", fg=typer.colors.YELLOW)
            raise typer.Exit()

    try:
        generator.generate(
            templates,
            output_file=output,
            append=append,
            offline=offline,
        )
    except (OSError, RuntimeError, ValueError) as error:
        typer.secho(f"❌ Error generating .gitignore: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
