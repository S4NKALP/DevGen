import sys
import questionary
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
    render_custom_template,
)
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.theme import Theme


class CommitEngineError(Exception):
    """Exception raised for errors in the commit engine."""

    pass


# Token Optimization Constants
MAX_DIFF_SIZE = 8000  # Maximum characters for a single group diff
IGNORE_PATTERNS = [
    "uv.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "composer.lock",
    "Gemfile.lock",
    "poetry.lock",
]


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
        check: bool = False,
        provider: str = "gemini",
        model: str = "gemini-2.5-flash",
        logger: Any | None = None,
        **kwargs,
    ):
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
            # Get modified, deleted and untracked files
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
            files = [f.strip() for f in out.split("\n") if f.strip()]

            # Also get staged files (in case of a previous failed run)
            staged_out = run_git_command(["git", "diff", "--name-only", "--cached"])
            staged_files = [f.strip() for f in staged_out.split("\n") if f.strip()]

            # Combine and deduplicate
            all_files = list(set(files + staged_files))
            return all_files
        except subprocess.CalledProcessError as e:
            msg = f"Git command failed: {' '.join(e.cmd)}\nError: {e.stderr.strip()}"
            self.logger.error(msg)
            raise CommitEngineError(msg) from e

    def group_files(self, files: List[str]) -> Dict[str, List[str]]:
        """Groups files by their parent directory with smart merging if limit is exceeded."""
        max_groups = self.config.get("max_groups", 5)

        # 1. Initial grouping by immediate parent
        groups = defaultdict(list)
        for f in files:
            parent = str(Path(f).parent)
            key = "root" if parent == "." else parent
            groups[key].append(f)

        if len(groups) <= max_groups:
            return dict(groups)

        self.logger.info(
            f"Too many groups ({len(groups)}). Merging based on max_groups={max_groups}"
        )

        # 2. Iteratively merge the deepest group into its parent until we hit the limit
        while len(groups) > max_groups:
            # Find the deepest path among the current group keys
            # Skip 'root' as it's the top level
            potential_merges = [k for k in groups.keys() if k != "root"]
            if not potential_merges:
                # This could happen if only 'root' is left or if max_groups is very small
                break

            # Deepest path is the one with the most segments
            deepest = max(potential_merges, key=lambda p: len(Path(p).parts))

            # Find the parent of this deepest path
            parent_path = str(Path(deepest).parent)
            new_key = "root" if parent_path == "." else parent_path

            # Merge files into the new key
            self.logger.debug(f"Merging group '{deepest}' into '{new_key}'")
            groups[new_key].extend(groups.pop(deepest))

        return dict(groups)

    def generate_diff(self, files: List[str]) -> str:
        """Generates diff for specific files, with truncation for token optimization."""
        try:
            # Filter out very large metadata files that don't need full diffs
            summary_info = []
            files_to_diff = []
            for f in files:
                if any(p in f for p in IGNORE_PATTERNS):
                    summary_info.append(f"[METADATA UPDATED] {f}")
                else:
                    files_to_diff.append(f)

            diff = ""
            if files_to_diff:
                diff = run_git_command(
                    ["git", "--no-pager", "diff", "--staged", "--", *files_to_diff]
                )

            full_content = "\n".join(summary_info + [diff]).strip()

            # Truncate if too large
            if len(full_content) > MAX_DIFF_SIZE:
                self.logger.info(
                    f"Truncating diff from {len(full_content)} to {MAX_DIFF_SIZE} chars"
                )
                half = MAX_DIFF_SIZE // 2
                return (
                    full_content[:half]
                    + "\n\n... [DIFF TRUNCATED FOR TOKEN OPTIMIZATION] ...\n\n"
                    + full_content[-half:]
                )

            return full_content
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
                # Check for "no upstream branch" specifically to give a hint?
                if "no upstream branch" in msg.lower():
                    self.console.print(
                        "[warning]No upstream branch. Skipping push.[/warning]"
                    )
                    return
                raise CommitEngineError(msg) from e
        self.console.print("[bold green]Push successful.[/bold green]")

    def _get_manifest_context(self) -> str:
        """Finds and reads manifest files to provide context."""
        manifests = [
            "pyproject.toml",
            "package.json",
            "go.mod",
            "Cargo.toml",
            "Gemfile",
            "requirements.txt",
            "uv.lock",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "composer.lock",
            "Gemfile.lock",
            "poetry.lock",
        ]
        found = []
        for m in manifests:
            path = Path(m)
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    # Take only first 100 lines to avoid token bloat
                    lines = content.splitlines()
                    summary = "\n".join(lines[:100])
                    if len(lines) > 100:
                        summary += "\n... (truncated)"
                    found.append(f"File: {m}\n---\n{summary}\n---")
                except Exception:
                    continue

        if not found:
            return ""

        return "\n\n### Project Context (Manifests)\n" + "\n".join(found)

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
        custom_template = self.config.get("custom_template")

        manifest_context = self._get_manifest_context()
        if manifest_context:
            self.logger.info("Including manifest context in prompt")

        if custom_template:
            self.logger.info("Using custom template from config")
            prompt = render_custom_template(
                custom_template,
                group_name=group,
                diff_text=diff,
                use_emoji=use_emoji,
                context=manifest_context,
            )
        else:
            template = self.template_env.get_template("commit_message.j2")
            prompt = template.render(
                group_name=group,
                diff_text=diff,
                use_emoji=use_emoji,
                context=manifest_context,
            )

        # Automatically append emoji instruction based on global setting
        emoji_instr = "Use emojis (🚀, 🐛)." if use_emoji else "No emojis."
        prompt = f"{prompt.strip()}\n\n- {emoji_instr}"

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
        try:
            if not msg:
                self.logger.error(f"Empty message for {group}")
                self._reset_group(files)
                return False

            if self.dry_run:
                self._log_dry_run(group, msg)
                self._reset_group(files)
            else:
                if self.check:
                    self.console.print(
                        Panel(
                            Markdown(msg),
                            title=f"Proposed Commit Message [group: {group}]",
                            border_style="cyan",
                        )
                    )
                    choice = questionary.select(
                        "How would you like to proceed?",
                        choices=[
                            "Confirm",
                            "Edit",
                            "Abort",
                        ],
                        default="Confirm",
                    ).ask()

                    if not choice or choice == "Abort":
                        self.logger.info(f"Commit aborted by user at group {group}")
                        self._reset_group(files)
                        raise KeyboardInterrupt("User aborted")

                    if choice == "Edit":
                        msg = questionary.text(
                            "Edit commit message:",
                            multiline=True,
                            default=msg,
                        ).ask()
                        if not msg:
                            self.logger.info(
                                f"Empty edit, commit cancelled for {group}"
                            )
                            self._reset_group(files)
                            return True

                self.commit_staged(msg)

            return True
        except Exception as e:
            self.logger.error(f"Failed to process group {group}: {e}")
            self._reset_group(files)
            return False

    def _reset_group(self, files: List[str]):
        """Unstages files for a group."""
        try:
            run_git_command(["git", "reset", "HEAD", "--", *files])
        except subprocess.CalledProcessError:
            pass  # Ignore reset errors

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
    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Commit engine failed: {e}", exc_info=True)


__all__ = ["run_commit_engine"]
