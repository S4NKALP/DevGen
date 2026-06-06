"""Shared section definitions for changelog and release-note generators.

Both generators render the same set of Conventional Commit groups; this
module is the single source of truth for the section name, the emoji,
and the display order.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class Section(str, Enum):
    """Sections in the order they should be rendered."""

    BREAKING = "BREAKING CHANGES"
    FEATURES = "Features"
    BUG_FIXES = "Bug Fixes"
    PERFORMANCE = "Performance"
    DOCUMENTATION = "Documentation"
    REFACTOR = "Refactor"
    TESTS = "Tests"
    STYLE = "Style"
    CHORE = "Chore"
    OTHER = "Other Changes"

    @classmethod
    def ordered(cls) -> tuple["Section", ...]:
        return tuple(cls)


@dataclass(frozen=True)
class SectionStyle:
    """Visual style for a section (emoji + name for the heading)."""

    emoji: str
    heading: str


# Default style for each section. Generators can override per output
# format (changelog vs. release notes).
DEFAULT_STYLES: Mapping[Section, SectionStyle] = {
    Section.BREAKING: SectionStyle("💥", "BREAKING CHANGES"),
    Section.FEATURES: SectionStyle("✨", "Features"),
    Section.BUG_FIXES: SectionStyle("🐛", "Bug Fixes"),
    Section.PERFORMANCE: SectionStyle("⚡", "Performance"),
    Section.DOCUMENTATION: SectionStyle("📚", "Documentation"),
    Section.REFACTOR: SectionStyle("♻️", "Refactor"),
    Section.TESTS: SectionStyle("✅", "Tests"),
    Section.STYLE: SectionStyle("💄", "Style"),
    Section.CHORE: SectionStyle("🔧", "Chore"),
    Section.OTHER: SectionStyle("🧹", "Other Changes"),
}


# Conventional commit type → Section mapping. Long-form aliases ("feature",
# "bug") are also accepted.
TYPE_TO_SECTION: Mapping[str, Section] = {
    "feat": Section.FEATURES,
    "feature": Section.FEATURES,
    "fix": Section.BUG_FIXES,
    "bug": Section.BUG_FIXES,
    "perf": Section.PERFORMANCE,
    "docs": Section.DOCUMENTATION,
    "refactor": Section.REFACTOR,
    "test": Section.TESTS,
    "style": Section.STYLE,
    "build": Section.CHORE,
    "ci": Section.CHORE,
    "chore": Section.CHORE,
}


def section_for_type(commit_type: str) -> Section:
    """Return the Section for a Conventional Commit ``type``.

    Unknown types fall back to :attr:`Section.OTHER`.
    """
    return TYPE_TO_SECTION.get(commit_type.lower(), Section.OTHER)
