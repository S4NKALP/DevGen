from pathlib import Path
from typing import Annotated

import toml
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
    """Displays the application version retrieved from pyproject.toml if the input value is True, then exits the program. If the version information cannot be found or the file is missing or malformed, outputs an error message before exiting.

    Args:
        value (bool): A boolean flag indicating whether to display the version and exit.

    Returns:
        None

    Raises:
        typer.Exit: Exits the program after attempting to display the version or an error message.
    """
    if value:
        try:
            pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
            pyproject_data = toml.load(pyproject_path)
            # Try standard PEP 621 first, then fallback
            version = pyproject_data.get("project", {}).get("version")
            if not version:
                version = (
                    pyproject_data.get("tool", {}).get("poetry", {}).get("version")
                )

            if version:
                typer.echo(f"devgen version: {version}")
            else:
                typer.secho(
                    "Error: Version not found in pyproject.toml",
                    fg=typer.colors.RED,
                    err=True,
                )
        except (FileNotFoundError, KeyError, Exception) as e:
            typer.secho(
                f"Error: Could not determine version: {e}",
                fg=typer.colors.RED,
                err=True,
            )
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
    """Displays the application version information when the --version or -v option is used. If the flag is set, shows the version and exits; otherwise, provides guidance on using other commands with devgen.

    Args:
        version (bool or None, optional): A flag indicating whether to display the application version, set via command-line options --version or -v. Defaults to None.

    Returns:
        None
    """
    pass


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
