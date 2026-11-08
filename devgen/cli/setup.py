import typer

from devgen.cli.wizard import run_config_wizard

app = typer.Typer(
    name="setup",
    help="⚙️ Setup and configuration management.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


@app.command("config")
def setup_config() -> None:
    """Interactively set up DevGen."""
    run_config_wizard()
