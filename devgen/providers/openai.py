from openai import OpenAI

from devgen.providers.base import BaseProvider


class OpenaiProvider(BaseProvider):
    """Generates content using OpenAI's Chat Completions API."""

    DISPLAY_NAME = "OpenAI"
    DEFAULT_MODEL = "gpt-4o"

    def _generate(self, prompt, api_key, model, **kwargs):
        kwargs.pop("debug", None)
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response.choices[0].message.content or ""
