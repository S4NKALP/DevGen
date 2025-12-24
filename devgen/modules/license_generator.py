import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class LicenseGenerator:
    """Generates license files from templates."""

    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "templates" / "licenses"

    def list_licenses(self) -> List[Dict[str, str]]:
        """Lists available license templates."""
        licenses = []
        if not self.templates_dir.exists():
            return []

        for file_path in self.templates_dir.glob("*.json"):
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    licenses.append(
                        {
                            "key": data.get("key", file_path.stem),
                            "name": data.get("name", "Unknown License"),
                            "description": data.get("description", ""),
                        }
                    )
            except Exception:
                continue

        # Sort by name
        return sorted(licenses, key=lambda x: x["name"])

    def get_license_template(self, key: str) -> Optional[Dict]:
        """Loads a specific license template by key."""
        # We assume key matches filename for simplicity, or we search.
        # Based on file listing, filenames match keys (e.g. mit.json -> mit)
        file_path = self.templates_dir / f"{key}.json"
        if not file_path.exists():
            return None

        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def render_license(self, key: str, author: str, year: str = "") -> str:
        """Renders the license content with placeholders replaced."""
        template_data = self.get_license_template(key)
        if not template_data:
            raise ValueError(f"License template '{key}' not found.")

        content = template_data.get("template", "")

        if not year:
            year = str(datetime.now().year)

        # Replace placeholders
        # Support various formats found in templates
        year_placeholders = ["[year]", "[yyyy]", "{{year}}", "<year>"]
        author_placeholders = [
            "[fullname]",
            "[name of copyright owner]",
            "{{author}}",
            "<name of author>",
            "[author]",
        ]

        for p in year_placeholders:
            content = content.replace(p, year)

        for p in author_placeholders:
            content = content.replace(p, author)

        return content
