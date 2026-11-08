"""Builds the prompt inputs for the commit engine.

Three small composable classes:

* :class:`FileGrouper` — groups a flat file list into per-commit folders
* :class:`DiffBuilder` — produces a (possibly truncated) staged diff
* :class:`ManifestInspector` — extracts a one-line-per-file project summary
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import toml

from devgen.utils import get_git_root, run_git_command

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


class DiffBuilder:
    """Produces a staged diff for a list of paths with truncation."""

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_DIFF_SIZE,
        cwd: Path | None = None,
        logger=None,
    ) -> None:
        self.max_size = max_size
        self.cwd = cwd or get_git_root()
        self.logger = logger

    def build(self, files: list[str]) -> str:
        summary, to_diff = self._partition(files)

        diff = ""
        if to_diff:
            diff = run_git_command(
                ["git", "--no-pager", "diff", "--staged", "--", *to_diff],
                cwd=self.cwd,
            )

        full = "\n".join(summary + [diff]).strip()
        return self._truncate(full) if len(full) > self.max_size else full

    @staticmethod
    def _partition(files: list[str]) -> tuple[list[str], list[str]]:
        summary, to_diff = [], []
        for file in files:
            if Path(file).name in IGNORED_DIFF_PATTERNS:
                summary.append(f"[METADATA UPDATED] {file}")
            else:
                to_diff.append(file)
        return summary, to_diff

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

    def group(self, files: list[str]) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = defaultdict(list)
        for file in files:
            parent = str(Path(file).parent)
            groups["root" if parent == "." else parent].append(file)

        while len(groups) > self.max_groups:
            deepest = max(
                (key for key in groups if key != "root"),
                key=lambda key: len(Path(key).parts),
                default=None,
            )
            if deepest is None:
                break

            parent = str(Path(deepest).parent)
            groups["root" if parent == "." else parent].extend(groups.pop(deepest))

        return dict(groups)


class ManifestInspector:
    """Extracts a compact one-line-per-file project summary.

    Dumping the first 100 lines of ``pyproject.toml``/``requirements.txt``
    is wasteful — most of it is build/tool config the model does not need.
    We extract just the project identity and the package list.
    """

    @staticmethod
    def summary(cwd: Path | None = None) -> str:
        cwd = cwd or get_git_root() or Path(".")
        parts = [
            part
            for part in (
                ManifestInspector._pyproject(cwd),
                ManifestInspector._package_json(cwd),
                ManifestInspector._requirements(cwd),
            )
            if part
        ]
        return "\nProject: " + " | ".join(parts) if parts else ""

    @staticmethod
    def _format(
        source: str,
        *,
        name: str | None = None,
        version: str | None = None,
        description: str | None = None,
        deps: list[str] | None = None,
    ) -> str | None:
        fields = [
            f"{key}={value}"
            for key, value in (
                ("name", name),
                ("version", version),
                ("description", description),
            )
            if value
        ]
        if deps:
            fields.append(f"deps={','.join(deps)}")
        return f"[{source}] {' '.join(fields)}" if fields else None

    @staticmethod
    def _pkg_name(spec: str) -> str:
        return re.split(r"[><=!~\[]", spec, 1)[0].strip()

    @staticmethod
    def _pyproject(cwd: Path) -> str | None:
        path = cwd / "pyproject.toml"
        if not path.exists():
            return None

        try:
            data = toml.load(path)
        except (OSError, ValueError):
            return None

        project = data.get("project", {}) if isinstance(data, dict) else {}
        deps = [
            name
            for name in (
                ManifestInspector._pkg_name(dep)
                for dep in project.get("dependencies") or []
            )
            if name
        ]
        return ManifestInspector._format(
            "pyproject.toml",
            name=project.get("name"),
            version=project.get("version"),
            description=project.get("description"),
            deps=deps,
        )

    @staticmethod
    def _package_json(cwd: Path) -> str | None:
        path = cwd / "package.json"
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

        dependencies = data.get("dependencies") or {}
        deps = list(dependencies) if isinstance(dependencies, dict) else []
        return ManifestInspector._format(
            "package.json",
            name=data.get("name"),
            version=data.get("version"),
            description=data.get("description"),
            deps=deps,
        )

    @staticmethod
    def _requirements(cwd: Path) -> str | None:
        path = cwd / "requirements.txt"
        if not path.exists():
            return None

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, ValueError):
            return None

        deps = [
            name
            for name in (
                ManifestInspector._pkg_name(line)
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            )
            if name
        ]
        return ManifestInspector._format("requirements.txt", deps=deps)
