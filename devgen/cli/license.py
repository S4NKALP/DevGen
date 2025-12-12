from datetime import datetime
from pathlib import Path

import questionary
import typer
from typing_extensions import Annotated

from devgen.modules.license_generator import LicenseGenerator

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

    from devgen.utils import get_questionary_style

    style = get_questionary_style()

    # 1. Select License
    choices = [
        questionary.Choice(
            title=f"{lic['name']} ({lic['key']})",
            value=lic["key"],
            description=lic["description"],
        )
        for lic in licenses
    ]

    license_key = questionary.select(
        "Select a License:",
        choices=choices,
        use_indicator=True,
        use_shortcuts=True,
        style=style,
    ).ask()

    if license_key is None:
        raise typer.Exit(code=130)

    if not license_key:
        raise typer.Exit()

    # 2. Enter Author Name
    # Try to guess from git config if possible, but for now just empty default
    author = questionary.text("Enter Author Name:", style=style).ask()
    if author is None:
        raise typer.Exit(code=130)

    if not author:
        typer.secho(" Author name is required.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 3. Enter Year
    current_year = str(datetime.now().year)
    year = questionary.text("Enter Year:", default=current_year, style=style).ask()
    if year is None:
        raise typer.Exit(code=130)

    # Generate
    try:
        content = generator.render_license(license_key, author, year)

        output_path = Path(output)
        if output_path.exists():
            overwrite = questionary.confirm(
                f"File {output} already exists. Overwrite?", default=False, style=style
            ).ask()
            if overwrite is None:
                raise typer.Exit(code=130)
            if not overwrite:
                typer.secho("Operation cancelled.", fg=typer.colors.YELLOW)
                raise typer.Exit()

        output_path.write_text(content, encoding="utf-8")
        typer.secho(f"\n License generated at {output_path}", fg=typer.colors.GREEN)

    except Exception as e:
        typer.secho(f"\n Failed to generate license: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
