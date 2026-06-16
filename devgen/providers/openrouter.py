from openai import OpenAI

from devgen.providers.base import BaseProvider


class OpenrouterProvider(BaseProvider):
    """Generates content using OpenRouter (OpenAI-compatible API)."""

    DISPLAY_NAME = "OpenRouter"
    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "openai/gpt-3.5-turbo"

    # Keys consumed by devgen itself — never forwarded to the SDK.
    _DEVGEN_KEYS = frozenset({"debug", "ollama_host", "max_retries", "retry_delay"})

    def _generate(self, prompt, api_key, model, **kwargs):
        safe_kwargs = {k: v for k, v in kwargs.items() if k not in self._DEVGEN_KEYS}
        with OpenAI(base_url=self.BASE_URL, api_key=api_key) as client:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": "https://github.com/S4NKALP/devgen",
                    "X-Title": "devgen CLI",
                },
                **safe_kwargs,
            )
        if not response.choices:
            raise RuntimeError(f"OpenRouter returned no choices for model {model!r}.")
        return response.choices[0].message.content or ""
