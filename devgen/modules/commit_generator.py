import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from devgen.ai import generate_with_ai
from devgen.utils import (
    configure_logger,
    extract_commit_messages,
    get_commit_dry_run_path,
    is_file_recent,
    load_template_env,
    run_git_command,
    sanitize_ai_commit_message,
)
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.theme import Theme


class CommitEngineError(Exception):
    """Exception raised for errors in the commit engine."""

    pass


class CommitEngine:
    """
    Engine for generating AI-powered commit messages.
    Handles detection of changes, grouping, AI generation, and git operations.
    """

    def __init__(
        self,
        dry_run: bool = False,
        push: bool = False,
        debug: bool = False,
        force_rebuild: bool = False,
        provider: str = "gemini",
        model: str = "gemini-2.5-flash",
        logger: Any | None = None,
        **kwargs,
    ):
        self.dry_run = dry_run
        self.push = push
        self.debug = debug
        self.force_rebuild = force_rebuild
        self.provider = provider
        self.model = model
        self.logger = logger or configure_logger(
            "devgen.commit",
            Path.home() / ".cache" / "devgen" / "commit.log",
            console=debug,
        )
        self.kwargs = kwargs
        self.dry_run_path = get_commit_dry_run_path()
        self.template_env = load_template_env("commit")

        self.console = Console(
            theme=Theme(
                {"info": "dim cyan", "warning": "magenta", "danger": "bold red"}
            )
        )

        # Load config from ~/.devgen.yaml
        from devgen.utils import load_config

        self.config = load_config()

    def detect_changes(self) -> List[str]:
        """Detects changed, deleted, or untracked files."""
        try:
            out = run_git_command(
                [
                    "git",
                    "ls-files",
                    "--deleted",
                    "--modified",
                    "--others",
                    "--exclude-standard",
                ]
            )
            return [f.strip() for f in out.split("\n") if f.strip()]
        except subprocess.CalledProcessError as e:
            msg = f"Git command failed: {' '.join(e.cmd)}\nError: {e.stderr.strip()}"
            self.logger.error(msg)
            raise CommitEngineError(msg) from e

    def group_files(self, files: List[str]) -> Dict[str, List[str]]:
        """Groups files by their parent directory."""
        groups = defaultdict(list)
        for f in files:
            parent = str(Path(f).parent)
            key = "root" if parent == "." else parent
            groups[key].append(f)
        return groups

    def generate_diff(self, files: List[str]) -> str:
        """Generates diff for specific files."""
        try:
            return run_git_command(
                ["git", "--no-pager", "diff", "--staged", "--", *files]
            )
        except subprocess.CalledProcessError as e:
            msg = f"Git command failed: {' '.join(e.cmd)}\nError: {e.stderr.strip()}"
            self.logger.error(msg)
            raise CommitEngineError(msg) from e

    def _init_dry_run(self):
        """Initializes the dry-run file."""
        self.dry_run_path.parent.mkdir(parents=True, exist_ok=True)
        with self.dry_run_path.open("w", encoding="utf-8") as f:
            ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S (%Z)")
            f.write(f"# Dry Run: Commit Messages\n_Generated: {ts}_\n\n")

    def _log_dry_run(self, group: str, msg: str):
        """Appends a dry-run entry and prints to console."""
        self.console.print(
            Panel(
                Markdown(msg),
                title=f"Dry Run: {group}",
                border_style="yellow",
                expand=False,
            )
        )
        with self.dry_run_path.open("a", encoding="utf-8") as f:
            f.write(f"## Group: `{group}`\n\n```md\n{msg}\n```\n\n---\n\n")

    def stage_files(self, files: List[str]):
        """Stages files in git."""
        if not files:
            return
        self.logger.info(f"Staging: {files}")
        self.console.print(f"[info]Staging {len(files)} files...[/info]")
        try:
            run_git_command(["git", "add", *files])
        except subprocess.CalledProcessError as e:
            msg = f"Git command failed: {' '.join(e.cmd)}\nError: {e.stderr.strip()}"
            self.logger.error(msg)
            raise CommitEngineError(msg) from e

    def commit_staged(self, msg: str):
        """Commits staged changes."""
        self.logger.info(f"Committing:\n{msg}")
        self.console.print(
            Panel(Markdown(msg), title="Commit Message", border_style="green")
        )
        try:
            run_git_command(["git", "commit", "-m", msg])
        except subprocess.CalledProcessError as e:
            msg = f"Git command failed: {' '.join(e.cmd)}\nError: {e.stderr.strip()}"
            self.logger.error(msg)
            raise CommitEngineError(msg) from e

    def push_commits(self):
        """Pushes commits to remote."""
        self.logger.info("Pushing to remote...")
        with self.console.status("[bold green]Pushing to remote...[/bold green]"):
            try:
                run_git_command(["git", "push"])
            except subprocess.CalledProcessError as e:
                msg = (
                    f"Git command failed: {' '.join(e.cmd)}\nError: {e.stderr.strip()}"
                )
                self.logger.error(msg)
                raise CommitEngineError(msg) from e
        self.console.print("[bold green]Push successful.[/bold green]")

    def generate_message(self, group: str, diff: str, cache: Dict[str, str]) -> str:
        """Generates a commit message using AI or cache."""
        if not self.force_rebuild and group in cache:
            self.logger.info(f"Using cached message for {group}")
            return cache[group]

        # Get settings from config or kwargs
        provider = (
            self.kwargs.get("provider") or self.config.get("provider") or self.provider
        )
        model = self.kwargs.get("model") or self.config.get("model") or self.model
        api_key = self.kwargs.get("api_key") or self.config.get("api_key")
        use_emoji = self.config.get("emoji", True)

        template = self.template_env.get_template("commit_message.j2")
        prompt = template.render(group_name=group, diff_text=diff, use_emoji=use_emoji)

        with self.console.status("[bold blue]Generating commit message...[/bold blue]"):
            raw = generate_with_ai(
                prompt,
                provider=provider,
                model=model,
                api_key=api_key,
                debug=self.debug,
                **self.kwargs,
            )
        return sanitize_ai_commit_message(raw)

    def is_ahead_of_remote(self) -> bool:
        """Checks if local branch has unpushed commits."""
        try:
            run_git_command(["git", "fetch", "origin"])
            count = run_git_command(
                ["git", "rev-list", "--count", "@{u}..HEAD"], check=False
            )
            if count and int(count) > 0:
                return True
        except (subprocess.CalledProcessError, CommitEngineError):
            # Maybe no upstream
            try:
                return bool(run_git_command(["git", "rev-parse", "HEAD"], check=False))
            except subprocess.CalledProcessError:
                return False
        return False

    def load_cache(self) -> Dict[str, str]:
        """Loads dry-run cache."""
        if self.dry_run:
            self._init_dry_run()
            return {}
        if not self.force_rebuild and is_file_recent(self.dry_run_path):
            self.logger.info(f"Loading cache from {self.dry_run_path}")
            return extract_commit_messages(self.dry_run_path)
        return {}

    def process_group(
        self, group: str, files: List[str], cache: Dict[str, str]
    ) -> bool:
        """Processes a single file group."""
        self.stage_files(files)
        diff = self.generate_diff(files)

        if not diff.strip():
            self.logger.info(f"Skipping empty diff for {group}")
            try:
                run_git_command(["git", "reset", "HEAD", "--", *files])
            except subprocess.CalledProcessError:
                pass  # Ignore reset errors
            return True

        msg = self.generate_message(group, diff, cache)
        if not msg:
            self.logger.error(f"Empty message for {group}")
            return False

        if self.dry_run:
            self._log_dry_run(group, msg)
            try:
                run_git_command(["git", "reset", "HEAD", "--", *files])
            except subprocess.CalledProcessError:
                pass
        else:
            self.commit_staged(msg)

        return True

    def execute(self):
        """Main execution method."""
        files = self.detect_changes()
        ahead = self.is_ahead_of_remote()

        if not files and not ahead:
            self.logger.info("Nothing to commit or push.")
            return

        failed = []
        if files:
            groups = self.group_files(files)
            cache = self.load_cache()

            for group, group_files in groups.items():
                try:
                    if not self.process_group(group, group_files, cache):
                        failed.append(group)
                except KeyboardInterrupt:
                    self.logger.warning("\nOperation interrupted by user.")
                    raise
        else:
            self.logger.info("No changes to commit, checking push...")

        if self.push and not self.dry_run:
            if not failed:
                self.push_commits()
            else:
                self.logger.error("Push aborted due to failed commits.")

        if self.dry_run:
            self.console.print(
                f"[bold green]Dry run done.[/bold green] See {self.dry_run_path}"
            )
        else:
            self.console.print("[bold green]Done.[/bold green]")
            if failed:
                self.console.print(f"[bold red]Failed groups: {failed}[/bold red]")


def run_commit_engine(**kwargs):
    """Entry point for the commit engine."""
    debug = kwargs.get("debug", False)
    logger = configure_logger("devgen.commit", console=debug)
    try:
        engine = CommitEngine(**kwargs)
        engine.execute()
    except Exception as e:
        logger.error(f"Commit engine failed: {e}", exc_info=True)


__all__ = ["run_commit_engine"]
