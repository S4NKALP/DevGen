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
    sanitize_ai_commit_message,
)


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
            "devgen.commit", Path.home() / ".cache" / "devgen" / "commit.log"
        )
        self.kwargs = kwargs
        self.dry_run_path = get_commit_dry_run_path()
        self.template_env = load_template_env("commit")

        # Load config from ~/.devgen.yaml
        from devgen.utils import load_config

        self.config = load_config()

    def _exec_git(self, args: List[str], allow_error: bool = False) -> str:
        """Executes a git command."""
        try:
            res = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=not allow_error,
            )
            return res.stdout.strip()
        except subprocess.CalledProcessError as e:
            msg = f"Git command failed: {' '.join(e.cmd)}\nError: {e.stderr.strip()}"
            self.logger.error(msg)
            raise CommitEngineError(msg) from e

    def detect_changes(self) -> List[str]:
        """Detects changed, deleted, or untracked files."""
        out = self._exec_git(
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
        return self._exec_git(["git", "--no-pager", "diff", "--staged", "--", *files])

    def _init_dry_run(self):
        """Initializes the dry-run file."""
        self.dry_run_path.parent.mkdir(parents=True, exist_ok=True)
        with self.dry_run_path.open("w", encoding="utf-8") as f:
            ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S (%Z)")
            f.write(f"# Dry Run: Commit Messages\n_Generated: {ts}_\n\n")

    def _log_dry_run(self, group: str, msg: str):
        """Appends a dry-run entry."""
        with self.dry_run_path.open("a", encoding="utf-8") as f:
            f.write(f"## Group: `{group}`\n\n```md\n{msg}\n```\n\n---\n\n")

    def stage_files(self, files: List[str]):
        """Stages files in git."""
        if not files:
            return
        self.logger.info(f"Staging: {files}")
        self._exec_git(["git", "add", *files])

    def commit_staged(self, msg: str):
        """Commits staged changes."""
        self.logger.info(f"Committing:\n{msg}")
        self._exec_git(["git", "commit", "-m", msg])

    def push_commits(self):
        """Pushes commits to remote."""
        self.logger.info("Pushing to remote...")
        self._exec_git(["git", "push"])
        self.logger.info("Push successful.")

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
            self._exec_git(["git", "fetch", "origin"])
            count = self._exec_git(
                ["git", "rev-list", "--count", "@{u}..HEAD"], allow_error=True
            )
            if count and int(count) > 0:
                return True
        except CommitEngineError:
            # Maybe no upstream
            return bool(self._exec_git(["git", "rev-parse", "HEAD"], allow_error=True))
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
            self._exec_git(["git", "reset", "HEAD", "--", *files])
            return True

        msg = self.generate_message(group, diff, cache)
        if not msg:
            self.logger.error(f"Empty message for {group}")
            return False

        if self.dry_run:
            self._log_dry_run(group, msg)
            self._exec_git(["git", "reset", "HEAD", "--", *files])
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
            self.logger.info(f"Dry run done. See {self.dry_run_path}")
        else:
            self.logger.info("Done.")
            if failed:
                self.logger.warning(f"Failed groups: {failed}")


def run_commit_engine(**kwargs):
    """Entry point for the commit engine."""
    logger = configure_logger("devgen.commit")
    try:
        engine = CommitEngine(**kwargs)
        engine.execute()
    except Exception as e:
        logger.error(f"Commit engine failed: {e}", exc_info=True)


__all__ = ["run_commit_engine"]
