"""Orchestrates the AI-powered commit flow.

The :class:`CommitEngine` is a thin coordinator. The real work lives in:

* :class:`devgen.modules.git_ops.GitOperator` — all git side-effects
* :class:`devgen.modules.diff_builder.FileGrouper` — files → commit groups
* :class:`devgen.modules.diff_builder.DiffBuilder` — staged diff + truncation
* :class:`devgen.modules.diff_builder.ManifestInspector` — project context
* :class:`devgen.ai.generate_with_ai` — provider-agnostic AI call
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    extract_commit_messages,
    get_commit_dry_run_path,
    is_file_recent,
    load_template_env,
    render_custom_template,
    sanitize_ai_commit_message,
)


class CommitEngineError(Exception):
    """Raised when the commit flow cannot proceed."""


class CacheManager:
    """Manages the dry-run cache file at ``~/.cache/devgen/commit_dry_run.md``."""

    def __init__(self, path: Path, max_age_minutes: int = 120) -> None:
        self.path = path
        self.max_age_minutes = max_age_minutes

    def init_dry_run(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S (%Z)")
        with self.path.open("w", encoding="utf-8") as f:
            f.write(f"# Dry Run: Commit Messages\n_Generated: {ts}_\n\n")

    def load(self, *, dry_run: bool, force_rebuild: bool) -> Dict[str, str]:
        if dry_run:
            self.init_dry_run()
            return {}
        if not force_rebuild and is_file_recent(self.path, self.max_age_minutes):
            return extract_commit_messages(self.path)
        return {}

    def append(self, group: str, message: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"## Group: `{group}`\n\n```md\n{message}\n```\n\n---\n\n")


class CommitMessageBuilder:
    """Renders the prompt and calls the AI provider."""

    def __init__(
        self,
        template_env,
        config: Dict[str, Any],
        provider: str,
        model: str,
        debug: bool = False,
    ) -> None:
        self.template_env = template_env
        self.config = config
        self.provider = provider
        self.model = model
        self.debug = debug

    def build_message(
        self,
        group: str,
        diff: str,
        manifest_context: str,
        extra_kwargs: Dict[str, Any],
    ) -> str:
        custom_template = self.config.get("custom_template")
        use_emoji = self.config.get("emoji", True)
        ollama_host = self.config.get("ollama_host")

        if custom_template:
            prompt = render_custom_template(
                custom_template,
                group_name=group,
                diff_text=diff,
                use_emoji=use_emoji,
                context=manifest_context,
            )
        else:
            prompt = (
                self.template_env.get_template("commit_message.tpl")
                .render(
                    group_name=group,
                    diff_text=diff,
                    use_emoji=use_emoji,
                    context=manifest_context,
                )
                .strip()
            )

        provider = (
            extra_kwargs.get("provider") or self.config.get("provider") or self.provider
        )
        model = extra_kwargs.get("model") or self.config.get("model") or self.model
        api_key = extra_kwargs.get("api_key") or self.config.get("api_key")

        call_kwargs = dict(extra_kwargs)
        if ollama_host and provider == "ollama":
            call_kwargs.setdefault("ollama_host", ollama_host)
        return generate_with_ai(
            prompt,
            provider=provider,
            model=model,
            api_key=api_key,
            debug=self.debug,
            **call_kwargs,
        )


class CommitEngine:
    """Coordinates the AI-powered commit flow.

    The constructor signature is stable (used by ``cli/commit.py``) but
    most logic now lives in composed objects. The public ``execute()``
    method remains the single entry point.
    """

    def __init__(
        self,
        dry_run: bool = False,
        push: bool = False,
        debug: bool = False,
        force_rebuild: bool = False,
        check: bool = False,
        provider: str = "gemini",
        model: str = "gemini-2.5-flash",
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
        self.provider = provider
        self.model = model
        self.logger = logger or configure_logger(
            "devgen.commit",
            Path.home() / ".cache" / "devgen" / "commit.log",
            console=debug,
        )
        self.kwargs = kwargs

        # CLI flags win over config; config wins over default.
        from devgen.utils import load_config

        self.config = load_config()

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
        self.template_env = load_template_env("commit")
        self.cache = CacheManager(get_commit_dry_run_path())
        self.message_builder = CommitMessageBuilder(
            self.template_env,
            self.config,
            provider=self.provider,
            model=self.model,
            debug=self.debug,
        )

    # ------------------------------------------------------------------ public

    def execute(self) -> None:
        files = self.git.detect_changed()
        # Only consult the remote state if the user wants to push —
        # avoids a network round-trip on every run.
        ahead = self.git.is_ahead_of_remote(fetch=self.push) if self.push else False

        if not files and not ahead:
            self.logger.info("Nothing to commit or push.")
            return

        failed: list[str] = []
        if files:
            failed = self._process_groups(files)

        if self.push and not self.dry_run:
            if not failed:
                self.git.push()
                self.console.print("[bold green]Push successful.[/bold green]")
            else:
                self.logger.error("Push aborted due to failed commits.")

        if self.dry_run:
            self.console.print(
                f"[bold green]Dry run done.[/bold green] See {self.cache.path}"
            )
        else:
            self.console.print("[bold green]Done.[/bold green]")
            if failed:
                self.console.print(f"[bold red]Failed groups: {failed}[/bold red]")

    # ------------------------------------------------------------------ groups

    def _process_groups(self, files: List[str]) -> list[str]:
        groups = self.grouper.group(files)
        cache_map = self.cache.load(
            dry_run=self.dry_run, force_rebuild=self.force_rebuild
        )
        failed: list[str] = []
        for i, (group, group_files) in enumerate(groups.items()):
            if not self._process_group(group, group_files, cache_map):
                failed.append(group)
            if len(groups) > 1 and i < len(groups) - 1:
                import time

                time.sleep(15)  # Conservative 4 RPM guard for free-tier
        return failed

    def _process_group(
        self,
        group: str,
        files: List[str],
        cache: Dict[str, str],
    ) -> bool:
        self.git.stage(files)
        diff = self.diff_builder.build(files)

        if not diff.strip():
            self.logger.info(f"Skipping empty diff for {group}")
            self.git.reset(files)
            return True

        if not self.force_rebuild and group in cache:
            self.logger.info(f"Using cached message for {group}")
            return self._apply_message(group, cache[group], files)

        try:
            manifest_context = ManifestInspector.summary()
            if manifest_context:
                self.logger.info("Including manifest context in prompt")
            with self.console.status(
                "[bold blue]Generating commit message...[/bold blue]"
            ):
                raw = self.message_builder.build_message(
                    group=group,
                    diff=diff,
                    manifest_context=manifest_context,
                    extra_kwargs=self.kwargs,
                )
            message = sanitize_ai_commit_message(raw)
        except Exception as e:
            self.logger.error(
                f"Failed to generate message for group {group!r}: {e}",
                exc_info=True,
            )
            self.git.reset(files)
            return False

        if not message:
            self.logger.error(f"Empty message for {group}")
            self.git.reset(files)
            return False

        return self._apply_message(group, message, files)

    def _apply_message(
        self,
        group: str,
        message: str,
        files: List[str],
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
        except Exception as e:
            self.logger.error(f"Failed to process group {group}: {e}", exc_info=True)
            self.git.reset(files)
            return False
        return True

    def _review_with_user(
        self,
        group: str,
        message: str,
        files: List[str],
    ) -> Optional[str]:
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
    debug = kwargs.get("debug", False)
    logger = configure_logger("devgen.cli.commit", console=debug)
    try:
        CommitEngine(**kwargs).execute()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Commit engine failed: {e}", exc_info=True)


__all__ = ["CommitEngine", "CommitEngineError", "run_commit_engine"]
