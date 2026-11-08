"""Small, dependency-light helpers shared across the package."""

import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path.home() / ".devgen.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "api_key": "",
    "emoji": True,
    "max_groups": 5,
    "ollama_host": "http://localhost:11434",
}


# --------------------------------------------------------------------------- paths


def ensure_log_directory() -> Path:
    log_dir = Path.home() / ".cache" / "devgen"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_main_log_path() -> Path:
    return ensure_log_directory() / "devgen.log"


def get_commit_dry_run_path() -> Path:
    return ensure_log_directory() / "commit_dry_run.md"


def is_file_recent(file_path: Path | str, max_age_minutes: int = 120) -> bool:
    try:
        age_seconds = time.time() - Path(file_path).stat().st_mtime
    except OSError:
        return False
    return age_seconds <= max_age_minutes * 60


# ------------------------------------------------------------------- commit text

_HEADER_RE = re.compile(
    r"^(feat|fix|chore|refactor|docs|style|test|build|ci|perf|revert|deps|wip)"
    r"(?:\([^)]*\))?!?: .+",
    re.IGNORECASE,
)

_LABEL_RE = re.compile(
    r"^(?:#+\s*)?(?:\d+\.?|\*|-)?\s*(?:Title|Commit Message|Message):\s*",
    re.IGNORECASE,
)


def sanitize_ai_commit_message(raw_text: str) -> str:
    """Return the first Conventional Commit block found in an AI response."""
    if not raw_text:
        return ""

    lines = raw_text.strip().splitlines()

    for index, line in enumerate(lines):
        candidate = _LABEL_RE.sub("", line.replace("**", "").strip()).strip()
        if not _HEADER_RE.match(candidate):
            continue

        message = [candidate]
        for following in lines[index + 1 :]:
            if "**Sponsor**" in following:
                break
            if following.strip().startswith("```"):
                continue
            message.append(following)
        return "\n".join(message).strip()

    # No Conventional Commit header: fall back to the first non-empty line.
    return next((line.strip() for line in lines if line.strip()), "")


def parse_markdown_sections(
    filepath: Path | str, marker_pattern: str
) -> dict[str, str]:
    path = Path(filepath)
    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8")
    return {
        key: value.strip()
        for key, value in re.findall(marker_pattern, content, re.DOTALL)
    }


def extract_commit_messages(filepath: Path | str) -> dict[str, str]:
    pattern = r"## Group: `(.*?)`\s*```md\n(.*?)\n```"
    return parse_markdown_sections(filepath, pattern)


# ------------------------------------------------------------------------ logging


def configure_logger(
    name: str = "devgen",
    log_file: Path | str | None = None,
    console: bool = True,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, mode="w", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# ---------------------------------------------------------------------------- git


def run_git_command(
    args: list[str],
    check: bool = True,
    cwd: Path | None = None,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> str:
    """Run a git command and return its stripped stdout."""
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding=encoding,
        errors=errors,
        check=check,
        cwd=cwd,
    )
    return result.stdout.strip()


def get_git_root(cwd: Path | None = None) -> Path | None:
    """Return the repository root, or ``None`` outside a git repository."""
    try:
        output = run_git_command(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    except (subprocess.CalledProcessError, OSError):
        return None
    return Path(output) if output else None


def get_git_staged_files() -> list[str]:
    try:
        output = run_git_command(["git", "diff", "--name-only", "--cached"])
    except (subprocess.CalledProcessError, OSError):
        return []
    return [line for line in output.splitlines() if line.strip()]


# ------------------------------------------------------------------------ files


def read_file_content(filepath: Path | str) -> str | None:
    try:
        return Path(filepath).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def delete_file(filepath: Path | str) -> bool:
    try:
        Path(filepath).unlink()
    except OSError:
        return False
    return True


def load_template(sub_dir: str, name: str) -> str:
    """Load a packaged template file."""
    template_path = Path(__file__).resolve().parent / "templates" / sub_dir / name
    if not template_path.is_file():
        raise RuntimeError(
            f"Template not found: {template_path}. The installation may be corrupted."
        )
    return template_path.read_text(encoding="utf-8")


# -------------------------------------------------------------------- templating

_IF_BLOCK_RE = re.compile(
    r"\{%\s*if\s+(\w+)\s*%\}(.*?)(?:\{%\s*else\s*%\}(.*?))?\{%\s*endif\s*%\}",
    re.DOTALL,
)
_VARIABLE_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render_template(template_str: str, **context: Any) -> str:
    """Render ``{{ variable }}`` substitutions and ``{% if %}`` blocks."""

    def render_if(match: re.Match[str]) -> str:
        variable, truthy_block, falsy_block = match.groups()
        return truthy_block if context.get(variable) else (falsy_block or "")

    result = _IF_BLOCK_RE.sub(render_if, template_str)
    return _VARIABLE_RE.sub(
        lambda match: str(context.get(match.group(1), "")),
        result,
    )


# ------------------------------------------------------------------------- config


def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )


def load_config() -> dict[str, Any]:
    """Load the user config, creating it with defaults on first run."""
    if not CONFIG_PATH.exists():
        try:
            save_config(DEFAULT_CONFIG)
        except OSError as error:
            print(f"Warning: could not create {CONFIG_PATH}: {error}")
        return dict(DEFAULT_CONFIG)

    try:
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        print(f"Warning: could not read {CONFIG_PATH}: {error}")
        return dict(DEFAULT_CONFIG)

    if not isinstance(data, dict):
        print(f"Warning: {CONFIG_PATH} is not a mapping; using defaults.")
        return dict(DEFAULT_CONFIG)

    return {**DEFAULT_CONFIG, **data}


# ---------------------------------------------------------------------- AI errors

# Substrings used to identify token / context-length errors from AI providers.
_TOKEN_LIMIT_PATTERNS = (
    "context length",
    "context_length",
    "context_length_exceeded",
    "context window",
    "context window exceeded",
    "context_size",
    "maximum context",
    "max context",
    "max_tokens",
    "max tokens",
    "prompt is too long",
    "too many tokens",
    "token limit",
    "tokens in the prompt",
    "input is too long",
    "request too large",
    "request was too large",
    "string too long",
    "too long for the model",
    "reduce the length of the messages",
    "tokens_exceeded",
)


def is_token_limit_error(error: BaseException | str) -> bool:
    """Return True if the error looks like a model context/token overflow."""
    text = str(error).lower()
    return any(pattern in text for pattern in _TOKEN_LIMIT_PATTERNS)


def format_token_limit_error(
    provider: str,
    error: BaseException | str,
    *,
    group: str | None = None,
) -> str:
    """Build a short, actionable message for a context-window overflow."""
    scope = f" ({group})" if group else ""
    return (
        f"{provider}: diff exceeds context window{scope}. "
        f"Cut token usage: --max-groups N, --max-diff-size N, "
        f"or a larger-context model (gemini-2.5-flash, gpt-4o, claude-3-5-sonnet). "
        f"Details: {error}"
    )


# ----------------------------------------------------------------------- UI style


def get_questionary_style():
    from questionary import Style

    return Style(
        [
            ("qmark", "fg:#673ab7 bold"),
            ("question", "bold"),
            ("answer", "fg:#f44336 bold"),
            ("pointer", "fg:#673ab7 bold"),
            ("highlighted", "fg:#673ab7 bold"),
            ("selected", "fg:#cc5454"),
            ("separator", "fg:#cc5454"),
            ("instruction", ""),
            ("text", ""),
            ("disabled", "fg:#858585 italic"),
        ]
    )


__all__ = [
    "CONFIG_PATH",
    "DEFAULT_CONFIG",
    "configure_logger",
    "delete_file",
    "ensure_log_directory",
    "extract_commit_messages",
    "format_token_limit_error",
    "get_commit_dry_run_path",
    "get_git_root",
    "get_git_staged_files",
    "get_main_log_path",
    "get_questionary_style",
    "is_file_recent",
    "is_token_limit_error",
    "load_config",
    "load_template",
    "parse_markdown_sections",
    "read_file_content",
    "render_template",
    "run_git_command",
    "sanitize_ai_commit_message",
    "save_config",
]
