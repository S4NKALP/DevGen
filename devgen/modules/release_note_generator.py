from datetime import datetime
from pathlib import Path

from devgen.modules.changelog_generator import ChangelogGenerator
from devgen.utils import configure_logger


class ReleaseNotesGenerator(ChangelogGenerator):
    """Generate short, clean release notes from git history."""

    SECTION_EMOJIS = {
        "BREAKING CHANGES": "⚠️",
        "Features": "✨",
        "Bug Fixes": "🐛",
        "Documentation": "📚",
        "Refactor": "♻️",
        "Tests": "✅",
        "Chore": "🔧",
        "Style": "✨",
        "Other Changes": "🧹",
    }

    def __init__(self, logger=None):
        super().__init__(logger or configure_logger("devgen.releasenotes"))

    def generate_release_markdown(self, groups, version="Unreleased"):
        """Generate human-friendly release notes."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        md = [f"## 🚀 Release {version} — {date_str}\n"]

        order = [
            "BREAKING CHANGES",
            "Features",
            "Bug Fixes",
            "Documentation",
            "Other Changes",
        ]

        for section in order:
            commits = groups.get(section)
            if not commits:
                continue

            emoji = self.SECTION_EMOJIS.get(section, "")
            md.append(f"### {emoji} {section}")

            for c in commits:
                scope = f"**{c['scope']}**: " if c["scope"] else ""
                md.append(f"- {scope}{c['subject']}")

            md.append("")

        return "\n".join(md)

    def run(self, output_file="RELEASE-NOTES.md", version="Unreleased", from_ref=""):
        """Main logic: get commits → parse → generate → write."""
        raw_commits = self.get_commits(from_ref)
        if not raw_commits or not raw_commits[0]:
            print("❗ No commits found for release notes.")
            return

        parsed = self.parse_commits(raw_commits)
        md = self.generate_release_markdown(parsed, version=version)

        Path(output_file).write_text(md, encoding="utf-8")
        print(f" Release notes written to {output_file}")
