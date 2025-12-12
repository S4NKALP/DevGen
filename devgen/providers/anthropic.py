import anthropic


class AnthropicProvider:
    """Generates content using Anthropic's Claude models."""

    def generate(
        self, prompt: str, api_key: str, model: str = "claude-3-opus-20240229", **kwargs
    ) -> str:
        """Generates a response using the Anthropic API."""
        if not api_key:
            raise ValueError("Anthropic API key is required.")

        try:
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()
        except Exception as e:
            raise RuntimeError(f"Anthropic generation failed: {e}")
