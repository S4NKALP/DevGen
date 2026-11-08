from typing import Any

from openai import OpenAI

from devgen.providers.openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    """Generates content using a local Ollama server.

    Ollama exposes an OpenAI-compatible endpoint at ``/v1``, so the
    ``openai`` client is reused. The host defaults to
    ``http://localhost:11434`` and can be overridden with ``ollama_host``.
    """

    DISPLAY_NAME = "Ollama"
    REQUIRES_API_KEY = False
    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"
    ERROR_HINT = (
        "Is the Ollama server running? Start it with `ollama serve` and "
        "pull a model with `ollama pull <model>`."
    )

    def _client(self, api_key: str | None, **kwargs: Any) -> OpenAI:
        host = kwargs.get("ollama_host") or self.DEFAULT_HOST
        return OpenAI(
            base_url=f"{host.rstrip('/')}/v1",
            api_key=api_key or "ollama",
        )
