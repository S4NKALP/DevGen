import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from jinja2 import Environment, FileSystemLoader


def ensure_log_directory() -> Path:
    log_dir = Path.home() / ".cache" / "devgen"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_main_log_path() -> Path:
    return ensure_log_directory() / "devgen.log"


def get_commit_dry_run_path() -> Path:
    return ensure_log_directory() / "commit_dry_run.md"


def is_file_recent(file_path: Path | str, max_age_minutes: int = 120) -> bool:
    path = Path(file_path)
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) <= max_age_minutes * 60


def sanitize_ai_commit_message(raw_text: str) -> str:
    """
    Cleans up the AI-generated commit message.
    It looks for a conventional commit header and extracts everything from there.
    It handles bolded headers and common AI prefixes.
    """
    if not raw_text:
        return ""

    lines = raw_text.strip().split("\n")

    # Regex for conventional commit header (including optional bolding)
    # Examples:
    # - feat(root): summary
    # - **fix: bug fix**
    # - chore(deps)!: breaking change
    header_pattern = re.compile(
        r"^(\*\*)?(feat|fix|chore|refactor|docs|style|test|build|ci)(\(.*\))?!?: .*",
        re.IGNORECASE,
    )

    cleaned_lines = []
    found_header = False

    for line in lines:
        stripped = line.strip()
        if not found_header:
            # First, strip bolding if it wraps the whole line or parts of it
            # This is simpler than handling it in the regex
            candidate = stripped.replace("**", "").strip()

            # Clean the line by removing labels like "1. Title:", "### Message:", etc.
            clean_line = re.sub(
                r"^(#+\s+)?(\d+\.?|\*|-)?\s*(Title|Commit Message|Message):\s*",
                "",
                candidate,
                flags=re.IGNORECASE,
            ).strip()

            if header_pattern.match(clean_line):
                found_header = True
                cleaned_lines.append(clean_line)
        else:
            # If we hit another header or a known separator, we stop
            if "**Sponsor**" in line:
                break
            cleaned_lines.append(line)

    if cleaned_lines:
        return "\n".join(cleaned_lines).strip()

    # Fallback: if no conventional commit header found, just take the first non-empty line
    # to avoid failing completely, but log a warning if possible.
    for line in lines:
        if line.strip():
            return line.strip()

    return ""


def parse_markdown_sections(
    filepath: Path | str, marker_pattern: str
) -> dict[str, str]:
    path = Path(filepath)
    if not path.exists():
        return {}

    with path.open(encoding="utf-8") as f:
        content = f.read()

    results = {}
    matches = re.findall(marker_pattern, content, re.DOTALL)
    for key, value in matches:
        results[key] = value.strip()
    return results


def extract_commit_messages(filepath: Path | str) -> dict[str, str]:
    pattern = r"## Group: `(.*?)`\s*```md\n(.*?)\n```"
    return parse_markdown_sections(filepath, pattern)


def configure_logger(
    name: str = "devgen", log_file: Optional[Path | str] = None, console: bool = True
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    if console:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # File handler
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(path, mode="w", encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


def run_git_command(
    args: list[str],
    check: bool = True,
    cwd: Optional[Path] = None,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> str:
    """
    Executes a git command and returns the output.

    Args:
        args: List of command arguments (e.g., ["git", "status"]).
        check: Whether to raise an exception on non-zero exit code.
        cwd: Current working directory for the command.
        encoding: Output encoding.
        errors: Error handling strategy for encoding.

    Returns:
        The standard output of the command, stripped of leading/trailing whitespace.

    Raises:
        subprocess.CalledProcessError: If the command fails and check is True.
    """
    try:
        res = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding=encoding,
            errors=errors,
            check=check,
            cwd=cwd,
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Log the error if a logger is configured, but re-raise
        # We don't have access to a specific logger here easily without passing it in,
        # so we rely on the caller to handle logging if needed, or we could log to a default one.
        # For now, just re-raise as the caller expects.
        raise e


def get_git_staged_files() -> list[str]:
    try:
        output = run_git_command(["git", "diff", "--name-only", "--cached"])
        return [f for f in output.splitlines() if f.strip()]
    except subprocess.CalledProcessError:
        return []


def read_file_content(filepath: Path | str) -> Optional[str]:
    path = Path(filepath)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def delete_file(filepath: Path | str) -> bool:
    path = Path(filepath)
    if path.exists():
        path.unlink()
        return True
    return False


def load_template_env(sub_dir: str) -> Environment:
    template_dir = Path(__file__).parent / "templates" / sub_dir
    return Environment(loader=FileSystemLoader(template_dir))


def render_custom_template(template_str: str, **context) -> str:
    """Renders a Jinja2 template from a string."""
    env = Environment()
    template = env.from_string(template_str)
    return template.render(**context)


def load_config() -> Dict[str, Any]:
    config_path = Path.home() / ".devgen.yaml"

    if not config_path.exists():
        default_config = {
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "api_key": "",
            "emoji": True,
            "max_groups": 5,
        }
        try:
            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(default_config, f, default_flow_style=False)
            # We don't print here to avoid noise during normal execution
        except Exception as e:
            print(f"Warning: Failed to create default config at {config_path}: {e}")
            return {}

    try:
        with config_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Failed to load config from {config_path}: {e}")
        return {}


__all__ = [
    "ensure_log_directory",
    "get_main_log_path",
    "get_commit_dry_run_path",
    "is_file_recent",
    "sanitize_ai_commit_message",
    "extract_commit_messages",
    "configure_logger",
    "run_git_command",
    "get_git_staged_files",
    "read_file_content",
    "delete_file",
    "load_template_env",
    "load_config",
    "get_questionary_style",
]


def get_questionary_style():
    from questionary import Style

    return Style(
        [
            ("qmark", "fg:#673ab7 bold"),  # Token.QuestionMark
            ("question", "bold"),  # Token.Question
            ("answer", "fg:#f44336 bold"),  # Token.Answer
            ("pointer", "fg:#673ab7 bold"),  # Token.Pointer
            ("highlighted", "fg:#673ab7 bold"),  # Token.Selected
            ("selected", "fg:#cc5454"),  # Token.SelectedItem
            ("separator", "fg:#cc5454"),  # Token.Separator
            ("instruction", ""),  # Token.Instruction
            ("text", ""),  # Token.Text
            ("disabled", "fg:#858585 italic"),  # Token.Disabled
        ]
    )
