import re
import subprocess
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from devgen.modules.changelog_sections import (
    DEFAULT_STYLES,
    Section,
    SectionStyle,
    section_for_type,
)
from devgen.utils import configure_logger, run_git_command


class ChangelogGenerator:
    """Generates a changelog from git history using Semantic Release style."""

    #: Conventional commit header: ``type(scope)!: subject``
    _CC_PATTERN = re.compile(r"^(\w+)(?:\(([^)]+)\))?(!?):\s+(.*)")

    def __init__(self, logger=None):
        self.logger = logger or configure_logger("devgen.changelog")

    # ------------------------------------------------------------------ commits

    def get_commits(self, from_ref: str = "", to_ref: str = "HEAD") -> list[str]:
        """Fetch commit lines in the requested range."""
        range_spec = self._resolve_range(from_ref, to_ref)
        command = [
            "git",
            "log",
            "--format=%H|%an|%ad|%s|%b%x00",
            "--date=short",
        ]
        if range_spec:
            command.append(range_spec)

        output = run_git_command(command)
        return [commit for commit in output.split("\0") if commit.strip()]

    def _resolve_range(self, from_ref: str, to_ref: str) -> str:
        if from_ref:
            return f"{from_ref}..{to_ref}"

        try:
            last_tag = run_git_command(["git", "describe", "--tags", "--abbrev=0"])
        except subprocess.CalledProcessError:
            self.logger.info("No tags found; using full history.")
            return ""

        self.logger.info(f"Generating changelog from last tag: {last_tag}")
        return f"{last_tag}..{to_ref}"

    # ----------------------------------------------------------------- parsing

    def parse_commits(self, raw_commits: list[str]) -> dict[Section, list[dict]]:
        """Group raw commit lines into :class:`Section` buckets."""
        groups: dict[Section, list[dict]] = defaultdict(list)
        for line in raw_commits:
            entry = self._parse_line(line)
            if entry is None:
                continue

            groups[section_for_type(entry["type"])].append(entry)
            if entry["breaking"]:
                groups[Section.BREAKING].append(entry)

        return dict(groups)

    def _parse_line(self, line: str) -> dict | None:
        line = line.strip()
        if not line:
            return None

        parts = line.split("|", 4)
        if len(parts) < 4:
            return None

        commit_hash, author, date, subject = parts[:4]
        body = parts[4] if len(parts) > 4 else ""

        match = self._CC_PATTERN.match(subject)
        if not match:
            return {
                "type": "",
                "hash": commit_hash,
                "author": author,
                "date": date,
                "scope": None,
                "subject": subject,
                "body": body,
                "breaking": False,
            }

        commit_type, scope, breaking, parsed_subject = match.groups()
        return {
            "type": commit_type,
            "hash": commit_hash,
            "author": author,
            "date": date,
            "scope": scope,
            "subject": parsed_subject,
            "body": body,
            "breaking": bool(breaking),
        }

    # ------------------------------------------------------------------ output

    def generate_markdown(
        self,
        groups: dict[Section, list[dict]],
        version: str = "Unreleased",
    ) -> str:
        """Render groups as a markdown changelog block."""
        return self._render(
            groups,
            title=f"## {version} ({datetime.now():%Y-%m-%d})",
            styles=DEFAULT_STYLES,
            heading_level="##",
        )

    def _render(
        self,
        groups: dict[Section, list[dict]],
        *,
        title: str,
        styles: Mapping[Section, SectionStyle],
        heading_level: str,
        include_hash: bool = True,
    ) -> str:
        lines = [title]
        for section in Section.ordered():
            commits = groups.get(section)
            if not commits:
                continue

            style = styles[section]
            lines.extend(["", f"{heading_level} {style.emoji} {style.heading}"])
            for commit in commits:
                scope = f"**{commit['scope']}**: " if commit.get("scope") else ""
                suffix = f" ({commit['hash'][:7]})" if include_hash else ""
                lines.append(f"- {scope}{commit['subject']}{suffix}")

        return "\n".join(lines) + "\n"

    def run(self, output_file: str | None = "CHANGELOG.md", from_ref: str = ""):
        """Fetch → parse → write (or print) the changelog."""
        raw_commits = self.get_commits(from_ref)
        if not raw_commits:
            self.logger.warning("No commits found.")
            return

        markdown = self.generate_markdown(self.parse_commits(raw_commits))

        if not output_file:
            print(markdown)
            return

        path = Path(output_file)
        if path.exists():
            old = path.read_text(encoding="utf-8")
            if old.strip().startswith("# CHANGELOG"):
                header, _, rest = old.partition("\n")
                new_content = f"{header}\n\n{markdown}\n{rest}"
            else:
                new_content = f"# CHANGELOG\n\n{markdown}\n\n{old}"
        else:
            new_content = f"# CHANGELOG\n\n{markdown}"

        path.write_text(new_content, encoding="utf-8")
        self.logger.info(f"Changelog written to {output_file}")
        print(f" Changelog updated: {output_file}")
