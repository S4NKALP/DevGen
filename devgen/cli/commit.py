from typing import Annotated

import questionary
import typer

from devgen.modules.commit_generator import run_commit_engine
from devgen.utils import (
    configure_logger,
    delete_file,
    get_commit_dry_run_path,
    get_git_staged_files,
    get_main_log_path,
    read_file_content,
)

app = typer.Typer(
    name="commit",
    help="🚀 AI-powered semantic commit message generator.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


@app.command("run")
def run_commit(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Simulate the commit process without making changes.",
        ),
    ] = False,
    push: Annotated[
        bool,
        typer.Option(
            "--push",
            help="Automatically push changes to the remote repository.",
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Enable debug mode for detailed logging.",
        ),
    ] = False,
    force_rebuild: Annotated[
        bool,
        typer.Option(
            "--force-rebuild",
            help="Force regeneration of commit messages.",
        ),
    ] = False,
    check: Annotated[
        bool,
        typer.Option(
            "--check",
            help="Review/edit commit message before committing.",
        ),
    ] = False,
) -> None:
    log_file = get_main_log_path()
    logger = configure_logger("devgen.cli.commit", log_file, console=debug)
    logger.info(f"Log file: {log_file}")
    logger.info(
        f"Options: dry_run={dry_run}, push={push}, debug={debug}, force={force_rebuild}, check={check}"
    )

    run_commit_engine(
        dry_run=dry_run,
        push=push,
        debug=debug,
        force_rebuild=force_rebuild,
        check=check,
        logger=logger,
    )


@app.command("clear-cache")
def clear_cache() -> None:
    if delete_file(get_commit_dry_run_path()):
        typer.secho("Cache cleared.", fg=typer.colors.GREEN)
    else:
        typer.secho("[i] No cache found.", fg=typer.colors.YELLOW)


@app.command("list-cached")
def list_cached() -> None:
    content = read_file_content(get_commit_dry_run_path())
    if content:
        typer.secho("--- Cached Dry-Run ---", fg=typer.colors.CYAN)
        typer.echo(content)
    else:
        typer.secho("[i] No cache found.", fg=typer.colors.YELLOW)


@app.command("validate")
def validate() -> None:
    staged = get_git_staged_files()
    if staged:
        typer.secho(f"{len(staged)} staged file(s):", fg=typer.colors.GREEN)
        for f in staged:
            typer.echo(f"- {f}")
    else:
        typer.secho("[i] No staged files.", fg=typer.colors.RED)


@app.command("undo")
def undo_commit() -> None:
    """Undoes the last commit but keeps changes staged."""
    from devgen.utils import run_git_command

    try:
        # Check if there's at least one commit
        run_git_command(["git", "rev-parse", "HEAD"])
    except Exception:
        typer.secho("No commits found to undo.", fg=typer.colors.RED)
        return

    if questionary.confirm(
        "Are you sure you want to undo the last commit? (Changes will remain staged)",
        default=False,
    ).ask():
        try:
            run_git_command(["git", "reset", "--soft", "HEAD~1"])
            typer.secho(
                "Last commit undone. Changes are still staged.", fg=typer.colors.GREEN
            )
        except Exception as e:
            typer.secho(f"Failed to undo commit: {e}", fg=typer.colors.RED)
