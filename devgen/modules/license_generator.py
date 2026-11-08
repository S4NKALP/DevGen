import json
from datetime import datetime
from pathlib import Path


class LicenseGenerator:
    """Generates license files from packaged JSON templates."""

    _YEAR_PLACEHOLDERS = ("[year]", "[yyyy]", "{{year}}", "<year>")
    _AUTHOR_PLACEHOLDERS = (
        "[fullname]",
        "[name of copyright owner]",
        "{{author}}",
        "<name of author>",
        "[author]",
    )

    def __init__(self):
        self.templates_dir = (
            Path(__file__).resolve().parent.parent / "templates" / "licenses"
        )

    def _load_templates(self) -> dict[str, dict]:
        if not self.templates_dir.exists():
            return {}

        templates = {}
        for file_path in sorted(self.templates_dir.glob("*.json")):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            templates[data.get("key", file_path.stem)] = data
        return templates

    def list_licenses(self) -> list[dict[str, str]]:
        """List available license templates, sorted by display name."""
        licenses = [
            {
                "key": key,
                "name": data.get("name", "Unknown License"),
                "description": data.get("description", ""),
            }
            for key, data in self._load_templates().items()
        ]
        return sorted(licenses, key=lambda item: item["name"])

    def get_license_template(self, key: str) -> dict | None:
        """Load a license template by key."""
        return self._load_templates().get(key)

    def render_license(self, key: str, author: str, year: str = "") -> str:
        """Render the license content with placeholders replaced."""
        template = self.get_license_template(key)
        if not template:
            raise ValueError(f"License template '{key}' not found.")

        content = template.get("template", "")
        year = year or str(datetime.now().year)

        for placeholder in self._YEAR_PLACEHOLDERS:
            content = content.replace(placeholder, year)
        for placeholder in self._AUTHOR_PLACEHOLDERS:
            content = content.replace(placeholder, author)
        return content
