"""Encapsulates every ``git`` invocation the commit engine makes.

Higher-level code depends on this class instead of calling git directly,
so git error handling lives in one place.
"""

import subprocess
from pathlib import Path

from devgen.utils import configure_logger, get_git_root, run_git_command


class GitError(RuntimeError):
    """Raised when a git command exits non-zero."""


class GitOperator:
    """All git side-effects in one place."""

    def __init__(
        self,
        cwd: Path | None = None,
        logger=None,
        quiet_commands: bool = True,
    ) -> None:
        self.cwd = cwd or get_git_root()
        self.logger = logger or configure_logger("devgen.git")
        self.quiet_commands = quiet_commands

    def _run(self, args: list[str], *, check: bool = True) -> str:
        try:
            return run_git_command(args, check=check, cwd=self.cwd)
        except subprocess.CalledProcessError as error:
            command = " ".join(error.cmd) if error.cmd else "git"
            stderr = (error.stderr or "").strip()
            raise GitError(f"Git command failed: {command}\nError: {stderr}") from error

    # ------------------------------------------------------------------ queries

    def upstream(self) -> str:
        """Return the upstream branch name, or an empty string if none."""
        return self._run(
            [
                "git",
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{u}",
            ],
            check=False,
        )

    def is_ahead_of_remote(self, fetch: bool = False) -> bool:
        """Return True if local HEAD has commits that are not pushed."""
        upstream = self.upstream()
        if not upstream:
            return False

        if fetch:
            # Best-effort refresh; push will fail loudly later if needed.
            self._run(["git", "fetch", "origin", upstream], check=False)

        count = self._run(["git", "rev-list", "--count", "@{u}..HEAD"], check=False)
        return count.isdigit() and int(count) > 0

    def detect_changed(self) -> list[str]:
        """Return modified, deleted, and untracked files (deduplicated)."""
        output = self._run(
            [
                "git",
                "ls-files",
                "-z",
                "--deleted",
                "--modified",
                "--others",
                "--exclude-standard",
            ]
        )
        files = {name for name in output.split("\0") if name}

        staged = self._run(["git", "diff", "-z", "--name-only", "--cached"])
        files.update(name for name in staged.split("\0") if name)
        return sorted(files)

    # ------------------------------------------------------------------ actions

    def stage(self, files: list[str]) -> None:
        """Stage paths, including deletions, in a single git call."""
        if files:
            self._run(["git", "add", "--all", "--", *files])

    def commit(self, message: str) -> None:
        """Create a commit with the given message."""
        self._run(["git", "commit", "-m", message])

    def reset(self, files: list[str]) -> None:
        """Unstage paths. Best-effort: failures are ignored."""
        if files:
            self._run(["git", "reset", "HEAD", "--", *files], check=False)

    def push(self) -> None:
        """Push the current branch, warning instead of failing without upstream."""
        try:
            self._run(["git", "push"])
        except GitError as error:
            if "no upstream branch" not in str(error).lower():
                raise
            if not self.quiet_commands:
                self.logger.warning("No upstream branch. Skipping push.")
