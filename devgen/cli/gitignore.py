from typing import List, Optional

import questionary
import typer
from typing_extensions import Annotated

from devgen.modules.gitignore_generator import GitignoreGenerator

app = typer.Typer(
    name="gitignore",
    help="🙈 Generate .gitignore files from GitHub templates.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


@app.command("list")
def list_templates(
    cached: Annotated[
        bool, typer.Option("--cached", "-c", help="List only cached templates.")
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

        if not templates:
            typer.echo("No templates found.")
            return

        # Print in columns or just list
        typer.echo(", ".join(templates))

    except Exception as e:
        typer.secho(f" Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("generate")
def generate_gitignore(
    templates: Annotated[
        Optional[List[str]],
        typer.Argument(
            help="Names of templates to include (e.g. Python Node). If empty, interactive mode is used."
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
        # Interactive mode
        try:
            if offline:
                available = generator.list_cached_templates()
            else:
                typer.secho("Fetching templates list...", fg=typer.colors.YELLOW)
                available = generator.list_available_templates()

            if not available:
                typer.secho(" No templates available.", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            from devgen.utils import get_questionary_style

            style = get_questionary_style()

            # Interactive search loop
            selected_templates = []
            while True:
                # Filter out already selected
                choices = [t for t in available if t not in selected_templates]
                # Add "Done" option at the top
                choices.insert(0, "Done (Finish selection)")

                choice = questionary.autocomplete(
                    "Search for a template (type to search, select 'Done' to finish):",
                    choices=choices,
                    ignore_case=True,
                    match_middle=True,
                    validate=lambda x: x in choices or x == "",
                    style=style,
                ).ask()

                if choice is None:
                    raise typer.Exit(code=130)

                if not choice or choice.startswith("Done"):
                    break

                selected_templates.append(choice)
                typer.secho(f"➕ Added '{choice}'", fg=typer.colors.GREEN)

            templates = selected_templates

            if not templates:
                typer.secho("No templates selected.", fg=typer.colors.YELLOW)
                raise typer.Exit()

        except typer.Exit:
            raise
        except KeyboardInterrupt:
            typer.secho("\nCancelled by user", fg=typer.colors.YELLOW)
            raise typer.Exit()
        except Exception as e:
            typer.secho(f"❌ Error fetching templates: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    try:
        generator.generate(
            templates, output_file=output, append=append, offline=offline
        )
    except Exception as e:
        typer.secho(f"❌ Error generating .gitignore: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
