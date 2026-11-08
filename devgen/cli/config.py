from typing import Annotated, Any

import questionary
import typer
import yaml

from devgen.ai import PROVIDERS
from devgen.cli.wizard import ask, run_config_wizard
from devgen.utils import get_questionary_style, load_config, save_config

app = typer.Typer(
    name="config",
    help="🔧 Manage configuration values.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

_TRUE_VALUES = {"true", "yes", "1"}
_FALSE_VALUES = {"false", "no", "0"}


def _coerce(value: str) -> Any:
    """Convert common string values to bool/int; leave everything else alone."""
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    if normalized.lstrip("-").isdigit():
        return int(normalized)
    return value


@app.command("list")
def list_config() -> None:
    """Show all configuration values."""
    typer.echo(yaml.safe_dump(load_config(), sort_keys=False))


@app.command("edit")
def edit_config(
    key: Annotated[str | None, typer.Argument(help="Configuration key.")] = None,
    value: Annotated[str | None, typer.Argument(help="New value.")] = None,
) -> None:
    """Edit or add a single configuration value."""
    config = load_config()
    style = get_questionary_style()

    if not key:
        key = ask(
            questionary.select(
                "Select key to update:",
                choices=list(config),
                style=style,
            )
        )

    if value is None:
        current = config.get(key)
        if key == "provider":
            value = ask(
                questionary.select(
                    "Select AI Provider:",
                    choices=sorted(PROVIDERS),
                    default=str(current or "gemini"),
                    style=style,
                )
            )
        elif isinstance(current, bool):
            value = ask(
                questionary.select(
                    f"Select value for '{key}':",
                    choices=["True", "False"],
                    default=str(current),
                    style=style,
                )
            )
        else:
            value = ask(
                questionary.text(
                    f"Enter value for '{key}':",
                    default=str(current) if current is not None else "",
                    style=style,
                )
            )

    config[key] = _coerce(value)
    try:
        save_config(config)
    except OSError as error:
        typer.secho(f"❌ Failed to save config: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.secho(f" Set '{key}' to '{config[key]}'", fg=typer.colors.GREEN)


@app.command("set")
def set_config() -> None:
    """Run the interactive configuration wizard."""
    run_config_wizard()


@app.command("info")
def config_info() -> None:
    """Show information about configuration options and templates."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Custom Template Variables", box=None)
    table.add_column("Variable", style="cyan")
    table.add_column("Description", style="white")

    table.add_row("{{ group_name }}", "The folder name being committed (or 'root').")
    table.add_row("{{ diff_text }}", "The git diff of the changes.")
    table.add_row("{{ context }}", "Project context (manifest files content).")

    console.print(table)
    console.print(
        "\n[bold]Tip:[/bold] If you hardcode emojis in your template, the AI will "
        "likely include them regardless of the 'emoji' setting.",
        style="yellow",
    )
    console.print("\n[bold]Example Template:[/bold]")
    console.print(
        "custom_template: |\n  [type]: [desc]\n  \n  Diff: {{ diff_text }}\n",
        style="dim",
    )
