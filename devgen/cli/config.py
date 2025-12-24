from pathlib import Path
from typing import Any, Optional

import questionary
import typer
import yaml
from typing_extensions import Annotated

from devgen.utils import get_questionary_style, load_config

app = typer.Typer(
    name="config",
    help="🔧 Manage configuration values.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _save_config(config: dict[str, Any]) -> None:
    config_path = Path.home() / ".devgen.yaml"
    try:
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)
    except Exception as e:
        typer.secho(f"❌ Failed to save config: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("list")
def list_config() -> None:
    """Show all configuration values."""
    config = load_config()
    if not config:
        typer.echo("Configuration is empty.")
        return

    typer.echo(yaml.dump(config, default_flow_style=False))


@app.command("edit")
def edit_config(
    key: Annotated[Optional[str], typer.Argument(help="Configuration key.")] = None,
    value: Annotated[Optional[str], typer.Argument(help="New value.")] = None,
) -> None:
    """Edit a specific configuration value."""
    config = load_config()
    style = get_questionary_style()

    if not key:
        choices = list(config.keys())
        key = questionary.select(
            "Select key to update:", choices=choices, style=style
        ).ask()

        if not key:
            raise typer.Exit()

    if value is None:
        # Check if existing value is boolean to offer select
        current_val = config.get(key)

        if key == "provider":
            value = questionary.select(
                "Select AI Provider:",
                choices=["gemini", "openai", "huggingface", "openrouter", "anthropic"],
                default=str(current_val) if current_val else "gemini",
                style=style,
            ).ask()
            if value is None:
                raise typer.Exit(code=130)
        elif isinstance(current_val, bool):
            val_choice = questionary.select(
                f"Select value for '{key}':",
                choices=["True", "False"],
                default=str(current_val),
                style=style,
            ).ask()
            if val_choice is None:
                raise typer.Exit(code=130)
            value = val_choice
        else:
            value = questionary.text(
                f"Enter value for '{key}':",
                default=str(current_val) if current_val is not None else "",
                style=style,
            ).ask()

        if value is None:
            raise typer.Exit(code=130)

    # Basic type inference
    if isinstance(value, str):
        if value.lower() == "true":
            val = True
        elif value.lower() == "false":
            val = False
        elif value.isdigit():
            val = int(value)
        else:
            val = value
    else:
        val = value

    config[key] = val
    _save_config(config)
    typer.secho(f" Set '{key}' to '{val}'", fg=typer.colors.GREEN)


@app.command("set")
def set_config() -> None:
    """Run the interactive configuration wizard."""
    typer.secho("🛠️  Interactive Configuration Setup", fg=typer.colors.CYAN, bold=True)

    config = load_config()
    style = get_questionary_style()

    # Questions
    provider = questionary.select(
        "Select AI Provider:",
        choices=["gemini", "openai", "huggingface", "openrouter", "anthropic"],
        default=config.get("provider", "gemini"),
        style=style,
    ).ask()
    if provider is None:
        raise typer.Exit(code=130)

    model_default = config.get("model", "gemini-2.5-flash")

    model = questionary.text(
        "Enter Model Name:", default=model_default, style=style
    ).ask()
    if model is None:
        raise typer.Exit(code=130)

    api_key = questionary.password(
        "Enter API Key (leave empty to keep existing or none):", style=style
    ).ask()
    if api_key is None:
        raise typer.Exit(code=130)

    if not api_key:
        api_key = config.get("api_key", "")

    emoji_choice = questionary.select(
        "Use Emojis in Commit Messages?",
        choices=["Yes", "No"],
        default="Yes" if config.get("emoji", True) else "No",
        style=style,
    ).ask()
    if emoji_choice is None:
        raise typer.Exit(code=130)
    emoji = emoji_choice == "Yes"

    # Save Config
    new_config = {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "emoji": emoji,
    }

    # Merge with existing config to preserve other keys?
    # The setup wizard usually overwrites or defines the core keys.
    # Let's preserve other keys.
    config.update(new_config)

    _save_config(config)
    typer.secho("\nConfiguration saved.", fg=typer.colors.GREEN)
    typer.echo(yaml.dump(new_config, default_flow_style=False))


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
        "\n[bold]Tip:[/bold] If you hardcode emojis in your template, the AI will likely include them regardless of the 'emoji' setting.",
        style="yellow",
    )
    console.print("\n[bold]Example Template:[/bold]")
    console.print(
        "custom_template: |\n  [type]: [desc]\n  \n  Diff: {{ diff_text }}\n",
        style="dim",
    )
