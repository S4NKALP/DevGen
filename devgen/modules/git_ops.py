"""Encapsulates every ``git`` invocation the commit engine makes.

Wraps :func:`devgen.utils.run_git_command` with the project's preferred
error handling and turns raw CLI output into typed results. Higher-level
classes (:class:`CommitEngine`) depend on this instead of calling git
themselves, so the engine code stays focused on orchestration.
"""

import subprocess
from pathlib import Path
from typing import Optional

from devgen.utils import configure_logger, run_git_command


class GitError(RuntimeError):
    """Raised when a git command exits non-zero."""


class GitOperator:
    """All git side-effects in one place."""

    def __init__(
        self,
        cwd: Optional[Path] = None,
        logger=None,
        quiet_commands: bool = True,
    ) -> None:
        self.cwd = cwd
        self.logger = logger or configure_logger("devgen.git")
        self.quiet_commands = quiet_commands

    # ------------------------------------------------------------------ helpers

    def _run(self, args, *, check: bool = True) -> str:
        try:
            return run_git_command(args, check=check, cwd=self.cwd)
        except subprocess.CalledProcessError as e:
            cmd_str = " ".join(e.cmd) if e.cmd else "git"
            stderr = (e.stderr or "").strip()
            raise GitError(f"Git command failed: {cmd_str}\nError: {stderr}") from e

    def _format_error(self, e: subprocess.CalledProcessError) -> str:
        cmd_str = " ".join(e.cmd) if e.cmd else "git"
        return f"Git command failed: {cmd_str}\nError: {(e.stderr or '').strip()}"

    # ------------------------------------------------------------------ queries

    def has_upstream(self) -> bool:
        """Return True if the current branch tracks an upstream."""
        return bool(self.upstream())

    def upstream(self) -> str:
        """Return the upstream branch name, or empty string if none."""
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
        """Return True if local HEAD has unpushed commits.

        When ``fetch`` is True, refresh the upstream ref first — but only
        do that when the caller is about to push. Skipping the fetch by
        default avoids a network round-trip on every run and shrinks the
        TOCTOU window between fetch and rev-list.
        """
        upstream = self.upstream()
        if not upstream:
            return False
        if fetch:
            try:
                self._run(["git", "fetch", "origin", upstream], check=False)
            except GitError:
                pass
        try:
            count = self._run(["git", "rev-list", "--count", "@{u}..HEAD"], check=False)
            return bool(count) and int(count) > 0
        except (GitError, ValueError):
            return False

    def detect_changed(self) -> list[str]:
        """Return modified, deleted, and untracked files (deduplicated)."""
        out = self._run(
            [
                "git",
                "ls-files",
                "--deleted",
                "--modified",
                "--others",
                "--exclude-standard",
            ]
        )
        files = {f.strip() for f in out.split("\n") if f.strip()}
        staged_out = self._run(["git", "diff", "--name-only", "--cached"])
        files.update(f.strip() for f in staged_out.split("\n") if f.strip())
        return sorted(files)

    # ------------------------------------------------------------------ actions

    def stage(self, files: list[str]) -> None:
        """``git add`` the given paths."""
        if not files:
            return
        try:
            self._run(["git", "add", *files])
        except GitError as e:
            raise GitError(f"Could not stage files: {e}") from e

    def commit(self, message: str) -> None:
        """``git commit -m`` with the given message."""
        self._run(["git", "commit", "-m", message])

    def reset(self, files: list[str]) -> None:
        """Unstage the given paths. Errors are swallowed — best-effort."""
        if not files:
            return
        try:
            self._run(["git", "reset", "HEAD", "--", *files], check=False)
        except GitError:
            pass

    def push(self) -> None:
        """Fetch upstream then push. Falls back to a no-upstream warning."""
        upstream = self.upstream()
        if upstream:
            try:
                self._run(["git", "fetch", "origin", upstream], check=False)
            except GitError:
                pass
        try:
            self._run(["git", "push"])
        except GitError as e:
            if "no upstream branch" in str(e).lower():
                if not self.quiet_commands:
                    print("[warning]No upstream branch. Skipping push.[/warning]")
                return
            raise
