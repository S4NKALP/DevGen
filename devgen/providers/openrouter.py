from openai import OpenAI

from devgen.utils import format_token_limit_error, is_token_limit_error


class OpenrouterProvider:
    """Generates content using OpenRouter (OpenAI-compatible API)."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def generate(
        self, prompt: str, api_key: str, model: str = "openai/gpt-3.5-turbo", **kwargs
    ) -> str:
        """Generates a response using OpenRouter."""
        if not api_key:
            raise ValueError(
                "OpenRouter API key is missing. "
                "Set it via `devgen setup config` or pass --api-key."
            )

        try:
            client = OpenAI(
                base_url=self.BASE_URL,
                api_key=api_key,
            )

            # Remove debug from kwargs if present
            kwargs.pop("debug", None)

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": "https://github.com/S4NKALP/devgen",  # Optional
                    "X-Title": "devgen CLI",  # Optional
                },
                **kwargs,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if is_token_limit_error(e):
                raise RuntimeError(format_token_limit_error("OpenRouter", e)) from e
            raise RuntimeError(
                f"OpenRouter request failed: {e}. "
                "Verify the model id (e.g. `openai/gpt-4o`) and your API key credits."
            ) from e
