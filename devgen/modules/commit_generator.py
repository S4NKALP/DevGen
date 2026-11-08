"""Orchestrates the AI-powered commit flow.

The :class:`CommitEngine` coordinates the pieces that do the real work:

* :class:`devgen.modules.git_ops.GitOperator` — git side-effects
* :class:`devgen.modules.diff_builder.FileGrouper` — files → groups
* :class:`devgen.modules.diff_builder.DiffBuilder` — staged diff + truncation
* :class:`devgen.modules.diff_builder.ManifestInspector` — project context
* :func:`devgen.ai.generate_with_ai` — provider-agnostic AI call
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import questionary
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.theme import Theme

from devgen.ai import generate_with_ai
from devgen.modules.diff_builder import (
    DEFAULT_MAX_DIFF_SIZE,
    DiffBuilder,
    FileGrouper,
    ManifestInspector,
)
from devgen.modules.git_ops import GitOperator
from devgen.utils import (
    configure_logger,
    ensure_log_directory,
    extract_commit_messages,
    format_token_limit_error,
    get_commit_dry_run_path,
    is_file_recent,
    is_token_limit_error,
    load_config,
    load_template,
    render_template,
    sanitize_ai_commit_message,
)

# Constructor kwargs that select the model call; they must not be
# forwarded to the provider SDK as generation parameters.
_CONTROL_KWARGS = frozenset({"api_key"})

# Conservative pause between groups for free-tier rate limits.
_SECONDS_BETWEEN_GROUPS = 15


class CacheManager:
    """Reads and writes the dry-run cache at ``~/.cache/devgen/commit_dry_run.md``."""

    def __init__(self, path: Path, max_age_minutes: int = 120) -> None:
        self.path = path
        self.max_age_minutes = max_age_minutes

    def reset(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S (%Z)")
        self.path.write_text(
            f"# Dry Run: Commit Messages\n_Generated: {timestamp}_\n\n",
            encoding="utf-8",
        )

    def load(self) -> dict[str, str]:
        if not is_file_recent(self.path, self.max_age_minutes):
            return {}
        return extract_commit_messages(self.path)

    def append(self, group: str, message: str) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(f"## Group: `{group}`\n\n```md\n{message}\n```\n\n---\n\n")


class CommitEngine:
    """Coordinates the AI-powered commit flow."""

    def __init__(
        self,
        dry_run: bool = False,
        push: bool = False,
        debug: bool = False,
        force_rebuild: bool = False,
        check: bool = False,
        provider: str | None = None,
        model: str | None = None,
        logger: Any | None = None,
        max_groups: int | None = None,
        max_diff_size: int | None = None,
        **kwargs: Any,
    ) -> None:
        self.dry_run = dry_run
        self.push = push
        self.debug = debug
        self.force_rebuild = force_rebuild
        self.check = check
        self.logger = logger or configure_logger(
            "devgen.commit",
            ensure_log_directory() / "commit.log",
            console=debug,
        )
        self.kwargs = kwargs

        # Explicit constructor values win over config; config wins over defaults.
        self.config = load_config()
        self.provider = provider or self.config.get("provider") or "gemini"
        self.model = model or self.config.get("model") or "gemini-2.5-flash"

        self.console = Console(
            theme=Theme(
                {"info": "dim cyan", "warning": "magenta", "danger": "bold red"}
            )
        )
        self.git = GitOperator(logger=self.logger)
        self.grouper = FileGrouper(
            max_groups=(
                max_groups
                if max_groups is not None
                else self.config.get("max_groups", 5)
            )
        )
        self.diff_builder = DiffBuilder(
            max_size=(
                max_diff_size
                if max_diff_size is not None
                else self.config.get("max_diff_size", DEFAULT_MAX_DIFF_SIZE)
            ),
            logger=self.logger,
        )
        self.template_str = load_template("commit", "commit_message.tpl")
        self.cache = CacheManager(get_commit_dry_run_path())

    # ------------------------------------------------------------------ public

    def execute(self) -> list[str]:
        files = self.git.detect_changed()
        ahead = self.push and self.git.is_ahead_of_remote(fetch=True)

        if not files and not ahead:
            self.logger.info("Nothing to commit or push.")
            return []

        failed = self._process_groups(files) if files else []

        if self.push and not self.dry_run:
            if failed:
                self.logger.error("Push aborted due to failed commits.")
            else:
                self.git.push()
                self.console.print("[bold green]Push successful.[/bold green]")

        if self.dry_run:
            self.console.print(
                f"[bold green]Dry run done.[/bold green] See {self.cache.path}"
            )
        else:
            self.console.print("[bold green]Done.[/bold green]")

        if failed:
            self.console.print(f"[bold red]Failed groups: {failed}[/bold red]")

        return failed

    # ------------------------------------------------------------------ groups

    def _process_groups(self, files: list[str]) -> list[str]:
        groups = list(self.grouper.group(files).items())
        cached = {} if self.force_rebuild or self.dry_run else self.cache.load()
        if self.dry_run:
            self.cache.reset()

        failed: list[str] = []
        for index, (group, group_files) in enumerate(groups):
            if not self._process_group(group, group_files, cached):
                failed.append(group)
                continue

            if self.provider != "ollama" and index < len(groups) - 1:
                time.sleep(_SECONDS_BETWEEN_GROUPS)

        return failed

    def _process_group(
        self,
        group: str,
        files: list[str],
        cached: dict[str, str],
    ) -> bool:
        self.git.stage(files)
        diff = self.diff_builder.build(files)

        if not diff.strip():
            self.logger.info(f"Skipping empty diff for {group}")
            self.git.reset(files)
            return True

        if group in cached:
            self.logger.info(f"Using cached message for {group}")
            return self._apply_message(group, cached[group], files)

        try:
            manifest_context = ManifestInspector.summary(cwd=self.git.cwd)
            if manifest_context:
                self.logger.info("Including manifest context in prompt")
            with self.console.status(
                "[bold blue]Generating commit message...[/bold blue]"
            ):
                raw = self._generate_message(group, diff, manifest_context)
            message = sanitize_ai_commit_message(raw)
        except Exception as error:  # noqa: BLE001 - isolate provider failures per group
            self._report_generation_error(group, error)
            self.git.reset(files)
            return False

        if not message:
            self.logger.error(f"Empty message for {group}")
            self.git.reset(files)
            return False

        return self._apply_message(group, message, files)

    def _generate_message(self, group: str, diff: str, context: str) -> str:
        template = self.config.get("custom_template") or self.template_str
        prompt = render_template(
            template,
            group_name=group,
            diff_text=diff,
            use_emoji=self.config.get("emoji", True),
            context=context,
        ).strip()

        api_key = self.kwargs.get("api_key") or self.config.get("api_key")

        call_kwargs = {
            key: value
            for key, value in self.kwargs.items()
            if key not in _CONTROL_KWARGS
        }
        if self.provider == "ollama" and self.config.get("ollama_host"):
            call_kwargs.setdefault("ollama_host", self.config["ollama_host"])

        return generate_with_ai(
            prompt,
            provider=self.provider,
            model=self.model,
            api_key=api_key,
            debug=self.debug,
            **call_kwargs,
        )

    def _report_generation_error(self, group: str, error: Exception) -> None:
        if is_token_limit_error(error):
            message = format_token_limit_error(self.provider, error, group=group)
            self.console.print(f"[bold red]{message}[/bold red]")
            self.logger.error(message)
            return

        self.logger.exception(
            f"Failed to generate message for group {group!r}: {error}",
        )

    def _apply_message(
        self,
        group: str,
        message: str,
        files: list[str],
    ) -> bool:
        if self.dry_run:
            self.console.print(
                Panel(
                    Markdown(message),
                    title=f"Dry Run: {group}",
                    border_style="yellow",
                    expand=False,
                )
            )
            self.cache.append(group, message)
            self.git.reset(files)
            return True

        if self.check:
            message = self._review_with_user(group, message, files)
            if message is None:
                return False

        try:
            self.console.print(
                Panel(Markdown(message), title="Commit Message", border_style="green")
            )
            self.git.commit(message)
        except Exception:
            self.logger.exception(f"Failed to process group {group}")
            self.git.reset(files)
            return False
        return True

    def _review_with_user(
        self,
        group: str,
        message: str,
        files: list[str],
    ) -> str | None:
        """Present the message; return the final message, or None to abort."""
        self.console.print(
            Panel(
                Markdown(message),
                title=f"Proposed Commit Message [group: {group}]",
                border_style="cyan",
            )
        )
        choice = questionary.select(
            "How would you like to proceed?",
            choices=["Confirm", "Edit", "Abort"],
            default="Confirm",
        ).ask()

        if not choice or choice == "Abort":
            self.logger.info(f"Commit aborted by user at group {group}")
            self.git.reset(files)
            return None

        if choice == "Edit":
            edited = questionary.text(
                "Edit commit message:",
                multiline=True,
                default=message,
            ).ask()
            if not edited:
                self.logger.info(f"Empty edit, commit cancelled for {group}")
                self.git.reset(files)
                return None
            return edited

        return message


def run_commit_engine(**kwargs: Any) -> None:
    """Entry point used by the CLI."""
    logger = kwargs.pop("logger", None) or configure_logger(
        "devgen.cli.commit",
        console=kwargs.get("debug", False),
    )
    try:
        failed = CommitEngine(logger=logger, **kwargs).execute()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Exiting...")
        sys.exit(130)
    except Exception:
        logger.exception("Commit engine failed")
        sys.exit(1)

    if failed:
        sys.exit(1)


__all__ = ["CommitEngine", "run_commit_engine"]
