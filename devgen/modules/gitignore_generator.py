from pathlib import Path
from typing import List

import requests

from devgen.utils import configure_logger


class GitignoreGenerator:
    """Fetches and manages .gitignore templates from GitHub."""

    def __init__(self, logger=None):
        self.logger = logger or configure_logger("devgen.gitignore")
        self.cache_dir = Path.home() / ".cache" / "devgen" / "gitignore"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_url = "https://api.github.com/repos/github/gitignore/contents/"
        self.raw_url_base = "https://raw.githubusercontent.com/github/gitignore/main/"

    def list_available_templates(self) -> List[str]:
        """Lists available templates from GitHub."""
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [
                item["name"].replace(".gitignore", "")
                for item in data
                if item["name"].endswith(".gitignore")
            ]
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch templates: {e}")
            raise RuntimeError(f"Failed to fetch templates: {e}")

    def list_cached_templates(self) -> List[str]:
        """Lists cached templates."""
        if not self.cache_dir.exists():
            return []
        return [f.stem for f in self.cache_dir.glob("*.gitignore")]

    def get_template_content(
        self, name: str, use_cache: bool = True, offline: bool = False
    ) -> str:
        """Fetches template content from cache or GitHub."""
        cache_file = self.cache_dir / f"{name}.gitignore"

        if offline:
            if cache_file.exists():
                self.logger.info(f"Using cached template for {name}")
                return cache_file.read_text(encoding="utf-8")
            else:
                raise RuntimeError(
                    f"Template '{name}' not found in cache (offline mode)."
                )

        # Try to fetch from GitHub
        try:
            url = f"{self.raw_url_base}{name}.gitignore"
            response = requests.get(url, timeout=10)

            if response.status_code == 404:
                # Try with capitalized first letter if lowercase fails, though the list should be accurate
                # The GitHub repo is case-sensitive for raw URLs usually matching the filename.
                # The list_available_templates returns exact filenames (minus extension).
                # So if we use the name from the list, it should be correct.
                # However, if user inputs manually, we might need to handle case.
                raise RuntimeError(f"Template '{name}' not found on GitHub.")

            response.raise_for_status()
            content = response.text

            if use_cache:
                cache_file.write_text(content, encoding="utf-8")
                self.logger.info(f"Cached template for {name}")

            return content

        except requests.RequestException as e:
            if cache_file.exists():
                self.logger.warning(f"Failed to fetch {name}, using cache: {e}")
                return cache_file.read_text(encoding="utf-8")
            raise RuntimeError(f"Failed to fetch {name} and no cache available: {e}")

    def generate(
        self,
        templates: List[str],
        output_file: str = ".gitignore",
        append: bool = True,
        offline: bool = False,
    ):
        """Generates the .gitignore file."""
        content = ""
        for name in templates:
            try:
                tpl_content = self.get_template_content(name, offline=offline)
                content += f"\n### {name} ###\n{tpl_content}\n"
            except Exception as e:
                self.logger.error(str(e))
                print(f" Error fetching {name}: {e}")

        if not content:
            return

        mode = "a" if append else "w"
        path = Path(output_file)

        if path.exists() and append:
            print(f"Appending to {output_file}...")
        elif path.exists() and not append:
            print(f"Overwriting {output_file}...")
        else:
            print(f"Creating {output_file}...")

        with path.open(mode, encoding="utf-8") as f:
            f.write(content)

        print(f" Successfully wrote to {output_file}")
