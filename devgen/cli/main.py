from importlib.metadata import PackageNotFoundError, version
from typing import Annotated

import typer

from devgen.cli.changelog import app as changelog_app
from devgen.cli.commit import app as commit_app
from devgen.cli.config import app as config_app
from devgen.cli.gitignore import app as gitignore_app
from devgen.cli.license import app as license_app
from devgen.cli.release import app as release_app
from devgen.cli.setup import app as setup_app

app = typer.Typer(
    name="devgen",
    help="devgen-py: AI-Powered Git Commit & Release Automation.",
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _version_callback(value: bool) -> None:
    """Print the installed package version and exit."""
    if not value:
        return

    try:
        package_version = version("devgen-cli")
    except PackageNotFoundError:
        package_version = "unknown"

    typer.echo(f"devgen version: {package_version}")
    raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=_version_callback,
            is_eager=True,
            help="Show the application version and exit.",
        ),
    ] = None,
) -> None:
    """DevGen command-line entry point."""


app.add_typer(commit_app, name="commit")
app.add_typer(setup_app, name="setup")
app.add_typer(changelog_app, name="changelog")
app.add_typer(license_app, name="license")
app.add_typer(gitignore_app, name="gitignore")
app.add_typer(release_app, name="release")
app.add_typer(config_app, name="config")

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        print("\n\n Operation cancelled by user.")
        raise typer.Exit(code=130)
