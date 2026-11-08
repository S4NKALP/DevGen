from datetime import datetime
from pathlib import Path

from devgen.modules.changelog_generator import ChangelogGenerator
from devgen.modules.changelog_sections import DEFAULT_STYLES, Section, SectionStyle
from devgen.utils import configure_logger

# Release notes use the same sections as the changelog, with a stronger
# warning emoji for breaking changes.
RELEASE_NOTE_STYLES: dict[Section, SectionStyle] = {
    **DEFAULT_STYLES,
    Section.BREAKING: SectionStyle("⚠️", "BREAKING CHANGES"),
}


class ReleaseNotesGenerator(ChangelogGenerator):
    """Generate short, clean release notes from git history."""

    def __init__(self, logger=None):
        super().__init__(logger or configure_logger("devgen.releasenotes"))

    def generate_release_markdown(self, groups, version="Unreleased"):
        """Render a human-friendly release-notes block."""
        return self._render(
            groups,
            title=f"## 🚀 Release {version} — {datetime.now():%Y-%m-%d}",
            styles=RELEASE_NOTE_STYLES,
            heading_level="###",
            include_hash=False,
        )

    def run(self, output_file="RELEASE-NOTES.md", version="Unreleased", from_ref=""):
        """Fetch → parse → write release notes."""
        raw_commits = self.get_commits(from_ref)
        if not raw_commits:
            print("❗ No commits found for release notes.")
            return

        markdown = self.generate_release_markdown(
            self.parse_commits(raw_commits),
            version=version,
        )
        Path(output_file).write_text(markdown, encoding="utf-8")
        print(f" Release notes written to {output_file}")
