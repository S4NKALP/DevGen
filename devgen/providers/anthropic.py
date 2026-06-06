import anthropic

from devgen.utils import format_token_limit_error, is_token_limit_error


class AnthropicProvider:
    """Generates content using Anthropic's Claude models."""

    def generate(
        self, prompt: str, api_key: str, model: str = "claude-3-opus-20240229", **kwargs
    ) -> str:
        """Generates a response using the Anthropic API."""
        if not api_key:
            raise ValueError(
                "Anthropic API key is missing. "
                "Set it via `devgen setup config` or pass --api-key."
            )

        try:
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()
        except Exception as e:
            if is_token_limit_error(e):
                raise RuntimeError(format_token_limit_error("Anthropic", e)) from e
            raise RuntimeError(
                f"Anthropic generation failed: {e}. "
                "Check the model id and your account credits."
            ) from e
