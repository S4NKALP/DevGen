from openai import OpenAI

from devgen.providers.base import BaseProvider


class OpenaiProvider(BaseProvider):
    """Generates content using OpenAI's Chat Completions API."""

    DISPLAY_NAME = "OpenAI"
    DEFAULT_MODEL = "gpt-4o"

    # Keys consumed by devgen itself — never forwarded to the SDK.
    _DEVGEN_KEYS = frozenset({"debug", "ollama_host", "max_retries", "retry_delay"})

    def _generate(self, prompt, api_key, model, **kwargs):
        safe_kwargs = {k: v for k, v in kwargs.items() if k not in self._DEVGEN_KEYS}
        with OpenAI(api_key=api_key) as client:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **safe_kwargs,
            )
        if not response.choices:
            raise RuntimeError(f"OpenAI returned no choices for model {model!r}.")
        return response.choices[0].message.content or ""
