"""Interactive configuration wizard shared by the CLI commands."""

from typing import Any

import questionary
import typer
import yaml

from devgen.ai import PROVIDERS
from devgen.utils import CONFIG_PATH, get_questionary_style, load_config, save_config


def ask(question: Any) -> Any:
    """Run a questionary prompt, exiting cleanly when the user cancels."""
    answer = question.ask()
    if answer is None:
        raise typer.Exit(code=130)
    return answer


def run_config_wizard() -> dict[str, Any]:
    """Prompt for the core settings, save them, and return the new config."""
    typer.secho("🛠️  Interactive Configuration Setup", fg=typer.colors.CYAN, bold=True)

    config = load_config()
    style = get_questionary_style()

    provider = ask(
        questionary.select(
            "Select AI Provider:",
            choices=sorted(PROVIDERS),
            default=config.get("provider", "gemini"),
            style=style,
        )
    )
    model = ask(
        questionary.text(
            "Enter Model Name:",
            default=config.get("model", "gemini-2.5-flash"),
            style=style,
        )
    )
    api_key = ask(
        questionary.password(
            "Enter API Key (leave empty to keep existing or none):",
            style=style,
        )
    ) or config.get("api_key", "")

    emoji_choice = ask(
        questionary.select(
            "Use Emojis in Commit Messages?",
            choices=["Yes", "No"],
            default="Yes" if config.get("emoji", True) else "No",
            style=style,
        )
    )

    ollama_host = config.get("ollama_host", "http://localhost:11434")
    if provider == "ollama":
        ollama_host = (
            ask(
                questionary.text(
                    "Ollama server URL:",
                    default=ollama_host,
                    style=style,
                )
            ).strip()
            or ollama_host
        )

    new_config = {
        **config,
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "emoji": emoji_choice == "Yes",
        "ollama_host": ollama_host,
    }
    try:
        save_config(new_config)
    except OSError as error:
        typer.secho(f"\nFailed to save configuration: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"\nConfiguration saved to {CONFIG_PATH}", fg=typer.colors.GREEN)
    typer.echo(yaml.safe_dump(new_config, sort_keys=False))
    return new_config
