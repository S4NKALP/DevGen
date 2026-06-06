from openai import OpenAI

from devgen.providers.base import BaseProvider
from devgen.utils import format_token_limit_error, is_token_limit_error


class OllamaProvider(BaseProvider):
    """Generates content using a local Ollama server.

    Ollama exposes an OpenAI-compatible endpoint at /v1/chat/completions,
    so we reuse the ``openai`` client. The host defaults to
    http://localhost:11434 but can be overridden via the ``ollama_host``
    kwarg (or ``ollama_host`` in ~/.devgen.yaml).
    """

    DISPLAY_NAME = "Ollama"
    REQUIRES_API_KEY = False
    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"

    def _generate(self, prompt, api_key, model, **kwargs):
        host = kwargs.get("ollama_host") or self.DEFAULT_HOST
        base_url = f"{host.rstrip('/')}/v1"
        kwargs.pop("debug", None)
        kwargs.pop("ollama_host", None)

        client = OpenAI(base_url=base_url, api_key=api_key or "ollama")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )

        if not response.choices:
            raise RuntimeError(
                f"Ollama returned no choices for model {model!r}. "
                "The model may not be installed locally."
            )
        return response.choices[0].message.content

    def _handle_error(self, error):
        """Override default wrapping — Ollama has no API key to check."""
        if is_token_limit_error(error):
            raise RuntimeError(
                format_token_limit_error(self.DISPLAY_NAME, error)
            ) from error
        raise RuntimeError(
            f"{self.DISPLAY_NAME} request failed: {error}. "
            "Is the Ollama server running? Start it with `ollama serve` and "
            "pull a model with `ollama pull <model>`."
        ) from error
