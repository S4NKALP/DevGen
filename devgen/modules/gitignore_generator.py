import re
from pathlib import Path

import requests

from devgen.utils import configure_logger

# Only allow safe characters in template names to prevent path traversal.
_TEMPLATE_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


class GitignoreGenerator:
    """Fetches and caches .gitignore templates from GitHub."""

    API_URL = "https://api.github.com/repos/github/gitignore/contents/"
    RAW_URL = "https://raw.githubusercontent.com/github/gitignore/main/"

    def __init__(self, logger=None):
        self.logger = logger or configure_logger("devgen.gitignore")
        self.cache_dir = Path.home() / ".cache" / "devgen" / "gitignore"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def list_available_templates(self) -> list[str]:
        """List template names available in the GitHub repository."""
        try:
            response = requests.get(self.API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as error:
            self.logger.error(f"Failed to fetch templates: {error}")
            raise RuntimeError(f"Failed to fetch templates: {error}") from error

        if not isinstance(data, list):
            raise RuntimeError(  # noqa: TRY004 - external API contract, not a type bug
                "GitHub returned an unexpected template list."
            )

        return [
            item["name"].removesuffix(".gitignore")
            for item in data
            if item.get("name", "").endswith(".gitignore")
        ]

    def list_cached_templates(self) -> list[str]:
        """List templates already stored in the local cache."""
        return sorted(file.stem for file in self.cache_dir.glob("*.gitignore"))

    def get_template_content(
        self,
        name: str,
        use_cache: bool = True,
        offline: bool = False,
    ) -> str:
        """Fetch template content from the cache or GitHub."""
        if not _TEMPLATE_NAME_RE.fullmatch(name):
            raise ValueError(
                f"Invalid template name '{name}'. Names may contain only "
                "alphanumerics, dots, hyphens, and underscores."
            )

        cache_file = self.cache_dir / f"{name}.gitignore"

        if offline:
            if not cache_file.exists():
                raise RuntimeError(
                    f"Template '{name}' not found in cache (offline mode)."
                )
            return cache_file.read_text(encoding="utf-8")

        try:
            response = requests.get(f"{self.RAW_URL}{name}.gitignore", timeout=10)
            if response.status_code == 404:
                raise RuntimeError(f"Template '{name}' not found on GitHub.")
            response.raise_for_status()
        except requests.RequestException as error:
            if cache_file.exists():
                self.logger.warning(f"Failed to fetch {name}, using cache: {error}")
                return cache_file.read_text(encoding="utf-8")
            raise RuntimeError(
                f"Failed to fetch {name} and no cache available: {error}"
            ) from error

        if use_cache:
            cache_file.write_text(response.text, encoding="utf-8")
            self.logger.info(f"Cached template for {name}")

        return response.text

    def generate(
        self,
        templates: list[str],
        output_file: str = ".gitignore",
        append: bool = True,
        offline: bool = False,
    ):
        """Generate a .gitignore file from one or more templates."""
        sections = []
        for name in templates:
            try:
                content = self.get_template_content(name, offline=offline)
            except (OSError, RuntimeError, ValueError) as error:
                self.logger.error(str(error))
                print(f" Error fetching {name}: {error}")
                continue
            sections.append(f"\n### {name} ###\n{content}\n")

        if not sections:
            return

        path = Path(output_file)
        if path.exists() and append:
            print(f"Appending to {output_file}...")
        elif path.exists():
            print(f"Overwriting {output_file}...")
        else:
            print(f"Creating {output_file}...")

        with path.open("a" if append else "w", encoding="utf-8") as file:
            file.write("".join(sections))

        print(f" Successfully wrote to {output_file}")
