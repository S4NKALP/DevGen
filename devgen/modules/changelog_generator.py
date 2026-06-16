import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from devgen.modules.changelog_sections import (
    DEFAULT_STYLES,
    Section,
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

    def get_commits(self, from_ref: str = "", to_ref: str = "HEAD") -> List[str]:
        """Fetch commit lines in the requested range."""
        if from_ref:
            range_spec = f"{from_ref}..{to_ref}"
            cmd = self._log_cmd(range_spec)
        else:
            cmd = self._resolve_range(to_ref)
        try:
            output = run_git_command(cmd)
            # Use %x00 as separator to avoid splitting on newlines in commit bodies
            # Then filter out empty strings
            return [c for c in output.split("\0") if c.strip()]
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git command failed: {e}")
            raise RuntimeError(f"Git command failed: {e}") from e

    def _log_cmd(self, range_spec: str) -> List[str]:
        # Format: hash|author|date|subject|body (separated by %x00 to avoid
        # splitting on newlines within commit bodies)
        return [
            "git",
            "log",
            "--format=%H|%an|%ad|%s|%b%x00",
            "--date=short",
            range_spec,
        ]

    def _resolve_range(self, to_ref: str) -> List[str]:
        try:
            last_tag = run_git_command(["git", "describe", "--tags", "--abbrev=0"])
            self.logger.info(f"Generating changelog from last tag: {last_tag}")
            return self._log_cmd(f"{last_tag}..HEAD")
        except (RuntimeError, subprocess.CalledProcessError):
            self.logger.info("No tags found, generating for all commits.")
            return ["git", "log", "--format=%H|%an|%ad|%s|%b%x00", "--date=short"]

    # ----------------------------------------------------------------- parsing

    def parse_commits(self, raw_commits: List[str]) -> Dict[Section, List[Dict]]:
        """Group raw commit lines into :class:`Section` buckets."""
        groups: Dict[Section, List[Dict]] = defaultdict(list)
        for line in raw_commits:
            entry = self._parse_line(line)
            if entry is None:
                continue
            section = section_for_type(entry["type"])
            entry["section"] = section
            if entry["breaking"]:
                groups[Section.BREAKING].append(entry)
            groups[section].append(entry)
        return dict(groups)

    def _parse_line(self, line: str) -> Dict | None:
        if not line.strip():
            return None
        parts = line.split("|", 4)
        if len(parts) < 4:
            return None
        commit_hash, author, date, subject = parts[:4]
        body = parts[4] if len(parts) > 4 else ""

        match = self._CC_PATTERN.match(subject)
        if match:
            c_type, c_scope, breaking, c_subject = match.groups()
            return {
                "type": c_type,
                "hash": commit_hash,
                "author": author,
                "date": date,
                "scope": c_scope,
                "subject": c_subject,
                "body": body,
                "breaking": bool(breaking),
            }
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

    # ------------------------------------------------------------------ output

    def generate_markdown(
        self,
        groups: Dict[Section, List[Dict]],
        version: str = "Unreleased",
    ) -> str:
        """Render groups as a markdown changelog block."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        out = [f"## {version} ({date_str})\n"]
        for section in Section.ordered():
            commits = groups.get(section)
            if not commits:
                continue
            style = DEFAULT_STYLES[section]
            out.append(f"## {style.emoji} {style.heading}\n")
            for c in commits:
                scope = f"**{c['scope']}**: " if c.get("scope") else ""
                out.append(f"- {scope}{c['subject']} ({c['hash'][:7]})")
            out.append("")
        return "\n".join(out)

    def run(self, output_file: Optional[str] = "CHANGELOG.md", from_ref: str = ""):
        """Fetch → parse → write (or print) the changelog."""
        raw_commits = self.get_commits(from_ref)
        if not raw_commits or not raw_commits[0]:
            self.logger.warning("No commits found.")
            return
        groups = self.parse_commits(raw_commits)
        md_content = self.generate_markdown(groups)

        if not output_file:
            print(md_content)
            return

        path = Path(output_file)
        if path.exists():
            old = path.read_text(encoding="utf-8")
            if old.strip().startswith("# CHANGELOG"):
                header, _, rest = old.partition("\n")
                new_content = f"{header}\n\n{md_content}\n{rest}"
            else:
                new_content = f"# CHANGELOG\n\n{md_content}\n\n{old}"
        else:
            new_content = f"# CHANGELOG\n\n{md_content}"
        path.write_text(new_content, encoding="utf-8")
        self.logger.info(f"Changelog written to {output_file}")
        print(f" Changelog updated: {output_file}")
