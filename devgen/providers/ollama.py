from devgen.utils import format_token_limit_error, is_token_limit_error


class OllamaProvider:
    """Generates content using a local Ollama server.

    Ollama exposes an OpenAI-compatible endpoint at /v1/chat/completions,
    so we can reuse the openai client. The host defaults to
    http://localhost:11434 but can be overridden via the
    `ollama_host` kwarg (or `ollama_host` in ~/.devgen.yaml).
    """

    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"

    def generate(
        self,
        prompt: str,
        api_key: str | None = None,
        model: str | None = None,
        **kwargs,
    ) -> str:
        from openai import OpenAI

        host = kwargs.get("ollama_host") or self.DEFAULT_HOST
        base_url = f"{host.rstrip('/')}/v1"
        chosen_model = model or self.DEFAULT_MODEL

        client = OpenAI(base_url=base_url, api_key=api_key or "ollama")

        kwargs.pop("debug", None)
        kwargs.pop("ollama_host", None)

        try:
            response = client.chat.completions.create(
                model=chosen_model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
        except Exception as e:
            if is_token_limit_error(e):
                raise RuntimeError(format_token_limit_error("Ollama", e)) from e
            raise RuntimeError(
                f"Ollama request failed (host={host}, model={chosen_model}): {e}. "
                "Is the Ollama server running? Start it with `ollama serve` and "
                "pull a model with `ollama pull <model>`."
            ) from e

        if not response.choices:
            raise RuntimeError(
                f"Ollama returned no choices for model {chosen_model!r}. "
                "The model may not be installed locally."
            )
        return response.choices[0].message.content.strip()
