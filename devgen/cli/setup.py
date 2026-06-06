from pathlib import Path

import questionary
import typer
import yaml

app = typer.Typer(
    name="setup",
    help="⚙️ Setup and configuration management.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


@app.command("config")
def setup_config() -> None:
    """Interactively setup configuration."""
    typer.secho("🛠️  Interactive Configuration Setup", fg=typer.colors.CYAN, bold=True)

    config_path = Path.home() / ".devgen.yaml"
    current_config = {}
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                current_config = yaml.safe_load(f) or {}
        except Exception:
            pass

    from devgen.utils import get_questionary_style

    style = get_questionary_style()

    # Questions
    provider = questionary.select(
        "Select AI Provider:",
        choices=[
            "gemini",
            "openai",
            "huggingface",
            "openrouter",
            "anthropic",
            "ollama",
        ],
        default=current_config.get("provider", "gemini"),
        style=style,
    ).ask()
    if provider is None:
        raise typer.Exit(code=130)

    model_default = current_config.get("model", "gemini-2.5-flash")

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
        api_key = current_config.get("api_key", "")

    emoji_choice = questionary.select(
        "Use Emojis in Commit Messages?",
        choices=["Yes", "No"],
        default="Yes" if current_config.get("emoji", True) else "No",
        style=style,
    ).ask()
    if emoji_choice is None:
        raise typer.Exit(code=130)
    emoji = emoji_choice == "Yes"

    ollama_host = current_config.get("ollama_host", "http://localhost:11434")
    if provider == "ollama":
        ollama_host_input = questionary.text(
            "Ollama server URL:",
            default=ollama_host,
            style=style,
        ).ask()
        if ollama_host_input is None:
            raise typer.Exit(code=130)
        ollama_host = ollama_host_input.strip() or ollama_host

    # Save Config — merge with existing to preserve extra keys
    new_config = {
        **current_config,
        **{
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "emoji": emoji,
            "ollama_host": ollama_host,
        },
    }

    try:
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(new_config, f, default_flow_style=False)
        typer.secho(f"\nConfiguration saved to {config_path}", fg=typer.colors.GREEN)
        typer.echo(yaml.dump(new_config, default_flow_style=False))
    except Exception as e:
        typer.secho(f"\nFailed to save configuration: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
