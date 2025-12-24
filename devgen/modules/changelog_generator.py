import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from devgen.utils import configure_logger, run_git_command


class ChangelogGenerator:
    """Generates a changelog from git history using Semantic Release style."""

    def __init__(self, logger=None):
        self.logger = logger or configure_logger("devgen.changelog")

    def get_commits(self, from_ref: str = "", to_ref: str = "HEAD") -> List[str]:
        """Fetches commit messages in the specified range."""
        range_spec = f"{from_ref}..{to_ref}" if from_ref else to_ref
        # Format: hash|author|date|subject|body
        fmt = "%H|%an|%ad|%s|%b"
        cmd = ["git", "log", f"--format={fmt}", "--date=short", range_spec]

        if not from_ref:
            # If no start ref, try to find the last tag
            try:
                last_tag = run_git_command(["git", "describe", "--tags", "--abbrev=0"])
                cmd = [
                    "git",
                    "log",
                    f"--format={fmt}",
                    "--date=short",
                    f"{last_tag}..HEAD",
                ]
                self.logger.info(f"Generating changelog from last tag: {last_tag}")
            except (RuntimeError, subprocess.CalledProcessError):
                self.logger.info("No tags found, generating for all commits.")
                cmd = ["git", "log", f"--format={fmt}", "--date=short"]

        try:
            return run_git_command(cmd).split("\n")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git command failed: {e}")
            raise RuntimeError(f"Git command failed: {e}")

    def parse_commits(self, raw_commits: List[str]) -> Dict[str, List[Dict]]:
        """Parses raw commit strings into structured data."""
        groups = defaultdict(list)
        # Conventional Commit Regex: type(scope)!: subject
        cc_pattern = re.compile(r"^(\w+)(?:\(([^)]+)\))?(!?):\s+(.*)")

        for line in raw_commits:
            if not line.strip():
                continue

            parts = line.split("|", 4)
            if len(parts) < 4:
                continue

            commit_hash, author, date, subject, body = (
                parts[0],
                parts[1],
                parts[2],
                parts[3],
                parts[4] if len(parts) > 4 else "",
            )

            match = cc_pattern.match(subject)
            if match:
                c_type, c_scope, breaking, c_subject = match.groups()
                entry = {
                    "hash": commit_hash,
                    "author": author,
                    "date": date,
                    "scope": c_scope,
                    "subject": c_subject,
                    "body": body,
                    "breaking": bool(breaking),
                }

                if breaking:
                    groups["BREAKING CHANGES"].append(entry)

                if c_type in ["feat", "feature"]:
                    groups["Features"].append(entry)
                elif c_type in ["fix", "bug"]:
                    groups["Bug Fixes"].append(entry)
                elif c_type in ["docs"]:
                    groups["Documentation"].append(entry)
                elif c_type in [
                    "style",
                    "refactor",
                    "perf",
                    "test",
                    "build",
                    "ci",
                    "chore",
                ]:
                    groups["Other Changes"].append(entry)
                else:
                    groups["Other Changes"].append(entry)
            else:
                # Non-conventional commits
                groups["Other Changes"].append(
                    {
                        "hash": commit_hash,
                        "author": author,
                        "date": date,
                        "scope": None,
                        "subject": subject,
                        "body": body,
                        "breaking": False,
                    }
                )

        return groups

    def generate_markdown(
        self, groups: Dict[str, List[Dict]], version: str = "Unreleased"
    ) -> str:
        """Generates markdown changelog from parsed commits."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        md = [f"## {version} ({date_str})\n"]

        # Order: Breaking, Features, Fixes, Docs, Others
        order = [
            "BREAKING CHANGES",
            "Features",
            "Bug Fixes",
            "Documentation",
            "Other Changes",
        ]

        emoji_map = {
            "BREAKING CHANGES": "💥 BREAKING CHANGES",
            "Features": "✨ Features",
            "Bug Fixes": "🐛 Bug Fixes",
            "Documentation": "📚 Documentation",
            "Other Changes": "🔨 Other Changes",
        }

        for section in order:
            commits = groups.get(section)
            if commits:
                header = emoji_map.get(section, section)
                md.append(f"## {header}\n")
                for c in commits:
                    scope = f"**{c['scope']}**: " if c["scope"] else ""
                    md.append(f"- {scope}{c['subject']} ({c['hash'][:7]})")
                md.append("")

        return "\n".join(md)

    def run(self, output_file: Optional[str] = "CHANGELOG.md", from_ref: str = ""):
        """Main execution method."""
        raw_commits = self.get_commits(from_ref)
        if not raw_commits or not raw_commits[0]:
            self.logger.warning("No commits found.")
            return

        parsed = self.parse_commits(raw_commits)
        md_content = self.generate_markdown(parsed)

        if output_file:
            path = Path(output_file)
            if path.exists():
                old_content = path.read_text(encoding="utf-8")
                # Prepend the new content, assume # CHANGELOG is at the top or needs to be
                if old_content.strip().startswith("# CHANGELOG"):
                    lines = old_content.split("\n", 1)
                    header = lines[0]
                    rest = lines[1] if len(lines) > 1 else ""
                    new_content = f"{header}\n\n{md_content}\n{rest.lstrip()}"
                else:
                    new_content = f"# CHANGELOG\n\n{md_content}\n\n{old_content}"
                path.write_text(new_content, encoding="utf-8")
            else:
                path.write_text(f"# CHANGELOG\n\n{md_content}", encoding="utf-8")

            self.logger.info(f"Changelog written to {output_file}")
            print(f" Changelog updated: {output_file}")
        else:
            print(md_content)
