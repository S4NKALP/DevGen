import anthropic

from devgen.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Generates content using Anthropic's Claude models."""

    DISPLAY_NAME = "Anthropic"
    DEFAULT_MODEL = "claude-3-opus-20240229"

    def _generate(self, prompt, api_key, model, **kwargs):
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
