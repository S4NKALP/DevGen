from openai import OpenAI

from devgen.providers.base import BaseProvider


class OpenrouterProvider(BaseProvider):
    """Generates content using OpenRouter (OpenAI-compatible API)."""

    DISPLAY_NAME = "OpenRouter"
    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "openai/gpt-3.5-turbo"

    def _generate(self, prompt, api_key, model, **kwargs):
        kwargs.pop("debug", None)
        client = OpenAI(base_url=self.BASE_URL, api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            extra_headers={
                "HTTP-Referer": "https://github.com/S4NKALP/devgen",
                "X-Title": "devgen CLI",
            },
            **kwargs,
        )
        return response.choices[0].message.content
