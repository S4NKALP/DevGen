"""Builds the prompt inputs for the commit engine.

Three small composable classes:

* :class:`FileGrouper` — groups a flat file list into per-commit folders
* :class:`DiffBuilder` — produces a (possibly truncated) staged diff
* :class:`ManifestInspector` — extracts a one-line-per-file project summary
"""

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from devgen.utils import run_git_command


# Lock files and other metadata blobs whose full diff would just bloat the
# prompt. We mark them as updated and skip the actual diff.
IGNORED_DIFF_PATTERNS = (
    "uv.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "composer.lock",
    "Gemfile.lock",
    "poetry.lock",
)

# Default cap for a single group diff. Real-world prompts above this size
# are likely to hit the model's context window; the cap is overridable
# via ``max_diff_size`` in the config.
DEFAULT_MAX_DIFF_SIZE = 8000

# Manifests we read for project context, in priority order. Lock files
# are excluded — they're noisy and rarely change in a way that informs
# a commit message.
_MANIFEST_FILES = (
    "pyproject.toml",
    "package.json",
    "requirements.txt",
)


class DiffBuilder:
    """Produces a staged diff for a list of paths with truncation."""

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_DIFF_SIZE,
        cwd: Optional[Path] = None,
        logger=None,
    ) -> None:
        self.max_size = max_size
        self.cwd = cwd
        self.logger = logger

    def build(self, files: List[str]) -> str:
        summary, to_diff = self._partition(files)
        diff = self._run_staged_diff(to_diff)
        full = "\n".join(summary + [diff]).strip()
        if len(full) > self.max_size:
            return self._truncate(full)
        return full

    # --- internals --------------------------------------------------------

    def _partition(self, files: List[str]) -> tuple[list[str], list[str]]:
        summary, to_diff = [], []
        for f in files:
            if Path(f).name in IGNORED_DIFF_PATTERNS:
                summary.append(f"[METADATA UPDATED] {f}")
            else:
                to_diff.append(f)
        return summary, to_diff

    def _run_staged_diff(self, files: List[str]) -> str:
        if not files:
            return ""
        try:
            return run_git_command(
                ["git", "--no-pager", "diff", "--staged", "--", *files],
                cwd=self.cwd,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Git command failed: {' '.join(e.cmd)}\nError: {e.stderr.strip()}"
            ) from e

    def _truncate(self, full: str) -> str:
        if self.logger is not None:
            self.logger.info(
                f"Truncating diff from {len(full)} to {self.max_size} chars "
                f"(config: max_diff_size). If you still hit token-limit errors, "
                f"lower this further or split the commit into more groups."
            )
        half = self.max_size // 2
        return (
            full[:half]
            + "\n\n... [DIFF TRUNCATED FOR TOKEN OPTIMIZATION] ...\n\n"
            + full[-half:]
        )


class FileGrouper:
    """Groups files by parent directory, merging down to ``max_groups``."""

    def __init__(self, max_groups: int = 5) -> None:
        self.max_groups = max(1, max_groups)

    def group(self, files: List[str]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = defaultdict(list)
        for f in files:
            parent = str(Path(f).parent)
            key = "root" if parent == "." else parent
            groups[key].append(f)
        if len(groups) <= self.max_groups:
            return dict(groups)
        return self._merge_deepest(dict(groups))

    def _merge_deepest(self, groups: Dict[str, List[str]]) -> Dict[str, List[str]]:
        while len(groups) > self.max_groups:
            candidates = [k for k in groups if k != "root"]
            if not candidates:
                break
            deepest = max(candidates, key=lambda p: len(Path(p).parts))
            parent_path = str(Path(deepest).parent)
            new_key = "root" if parent_path == "." else parent_path
            files = groups.pop(deepest)
            groups.setdefault(new_key, []).extend(files)
        return groups


class ManifestInspector:
    """Extracts a compact one-line-per-file project summary.

    Dumping the first 100 lines of ``pyproject.toml``/``requirements.txt``
    is extremely wasteful — most of it is build/tool config the model does
    not need. We extract just the project identity and the package list
    so the model can write context-aware commit messages.
    """

    @staticmethod
    def summary() -> str:
        lines = [
            s
            for s in (
                ManifestInspector._pyproject(),
                ManifestInspector._package_json(),
                ManifestInspector._requirements(),
            )
            if s
        ]
        if not lines:
            return ""
        return "\nProject: " + " | ".join(lines)

    # --- extractors -------------------------------------------------------

    @staticmethod
    def _pkg_name(spec: str) -> str:
        return re.split(r"[><=!~\[]", spec, 1)[0].strip()

    @staticmethod
    def _pyproject() -> Optional[str]:
        path = Path("pyproject.toml")
        if not path.exists():
            return None
        try:
            import toml

            data = toml.load(path)
        except Exception:
            return None
        proj = data.get("project", {}) if isinstance(data, dict) else {}
        parts = [
            f"{k}={proj[k]}" for k in ("name", "version", "description") if proj.get(k)
        ]
        deps = proj.get("dependencies") or []
        if deps:
            names = [n for n in (ManifestInspector._pkg_name(d) for d in deps) if n]
            if names:
                parts.append(f"deps={','.join(names)}")
        return f"[pyproject.toml] {' '.join(parts)}" if parts else None

    @staticmethod
    def _package_json() -> Optional[str]:
        path = Path("package.json")
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        parts = [
            f"{k}={data[k]}" for k in ("name", "version", "description") if data.get(k)
        ]
        deps = data.get("dependencies") or {}
        if isinstance(deps, dict) and deps:
            parts.append(f"deps={','.join(deps.keys())}")
        return f"[package.json] {' '.join(parts)}" if parts else None

    @staticmethod
    def _requirements() -> Optional[str]:
        path = Path("requirements.txt")
        if not path.exists():
            return None
        try:
            names = [
                n
                for n in (
                    ManifestInspector._pkg_name(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                )
                if n and not n.startswith("#")
            ]
        except Exception:
            return None
        return f"[requirements.txt] deps={','.join(names)}" if names else None
