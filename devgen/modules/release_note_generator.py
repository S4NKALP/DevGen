from datetime import datetime
from pathlib import Path

from devgen.modules.changelog_generator import ChangelogGenerator
from devgen.modules.changelog_sections import Section
from devgen.utils import configure_logger


# Release-note-specific heading styles (use the same emoji, simpler heading).
RELEASE_NOTE_STYLES = {
    Section.BREAKING: ("⚠️", "BREAKING CHANGES"),
    Section.FEATURES: ("✨", "Features"),
    Section.BUG_FIXES: ("🐛", "Bug Fixes"),
    Section.PERFORMANCE: ("⚡", "Performance"),
    Section.DOCUMENTATION: ("📚", "Documentation"),
    Section.REFACTOR: ("♻️", "Refactor"),
    Section.TESTS: ("✅", "Tests"),
    Section.STYLE: ("💄", "Style"),
    Section.CHORE: ("🔧", "Chore"),
    Section.OTHER: ("🧹", "Other Changes"),
}


class ReleaseNotesGenerator(ChangelogGenerator):
    """Generate short, clean release notes from git history."""

    def __init__(self, logger=None):
        super().__init__(logger or configure_logger("devgen.releasenotes"))

    def generate_release_markdown(self, groups, version="Unreleased"):
        """Render a human-friendly release-notes block."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        out = [f"## 🚀 Release {version} — {date_str}\n"]
        for section in Section.ordered():
            commits = groups.get(section)
            if not commits:
                continue
            emoji, heading = RELEASE_NOTE_STYLES[section]
            out.append(f"### {emoji} {heading}")
            for c in commits:
                scope = f"**{c['scope']}**: " if c.get("scope") else ""
                out.append(f"- {scope}{c['subject']}")
            out.append("")
        return "\n".join(out)

    def run(self, output_file="RELEASE-NOTES.md", version="Unreleased", from_ref=""):
        """Fetch → parse → write release notes."""
        raw_commits = self.get_commits(from_ref)
        if not raw_commits or not raw_commits[0]:
            print("❗ No commits found for release notes.")
            return

        groups = self.parse_commits(raw_commits)
        md = self.generate_release_markdown(groups, version=version)
        Path(output_file).write_text(md, encoding="utf-8")
        print(f" Release notes written to {output_file}")
