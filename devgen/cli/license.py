from datetime import datetime
from pathlib import Path
from typing import Annotated

import questionary
import typer

from devgen.cli.wizard import ask
from devgen.modules.license_generator import LicenseGenerator
from devgen.utils import get_questionary_style

app = typer.Typer(
    name="license",
    help="📄 Generate open source licenses.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


@app.command("generate")
def generate_license(
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Output file path.",
        ),
    ] = "LICENSE",
) -> None:
    """Interactively generate a license file."""
    generator = LicenseGenerator()
    licenses = generator.list_licenses()

    if not licenses:
        typer.secho(" No license templates found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    style = get_questionary_style()
    choices = [
        questionary.Choice(
            title=f"{license_info['name']} ({license_info['key']})",
            value=license_info["key"],
            description=license_info["description"],
        )
        for license_info in licenses
    ]

    license_key = ask(
        questionary.select(
            "Select a License:",
            choices=choices,
            use_indicator=True,
            use_shortcuts=True,
            style=style,
        )
    )

    author = ask(questionary.text("Enter Author Name:", style=style)).strip()
    if not author:
        typer.secho(" Author name is required.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    year = ask(
        questionary.text(
            "Enter Year:",
            default=str(datetime.now().year),
            style=style,
        )
    ).strip()

    output_path = Path(output)
    if output_path.exists():
        overwrite = ask(
            questionary.confirm(
                f"File {output} already exists. Overwrite?",
                default=False,
                style=style,
            )
        )
        if not overwrite:
            typer.secho("Operation cancelled.", fg=typer.colors.YELLOW)
            return

    try:
        content = generator.render_license(license_key, author, year)
        output_path.write_text(content, encoding="utf-8")
    except (OSError, ValueError) as error:
        typer.secho(f"\n Failed to generate license: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"\n License generated at {output_path}", fg=typer.colors.GREEN)
