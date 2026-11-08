from typing import ClassVar

from devgen.providers.openai_compatible import OpenAICompatibleProvider


class OpenrouterProvider(OpenAICompatibleProvider):
    """Generates content using OpenRouter (OpenAI-compatible API)."""

    DISPLAY_NAME = "OpenRouter"
    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "openai/gpt-3.5-turbo"
    DEFAULT_HEADERS: ClassVar[dict[str, str]] = {
        "HTTP-Referer": "https://github.com/S4NKALP/devgen",
        "X-Title": "devgen CLI",
    }
