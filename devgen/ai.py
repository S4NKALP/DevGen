"""Provider registry and dispatch for AI generation."""

from importlib import import_module
from typing import Any

from devgen.providers.base import BaseProvider

# Provider name -> (module, class). Keeping the registry explicit makes
# adding a provider a one-line change and avoids guessing class names.
PROVIDERS: dict[str, tuple[str, str]] = {
    "gemini": ("devgen.providers.gemini", "GeminiProvider"),
    "openai": ("devgen.providers.openai", "OpenaiProvider"),
    "anthropic": ("devgen.providers.anthropic", "AnthropicProvider"),
    "openrouter": ("devgen.providers.openrouter", "OpenrouterProvider"),
    "huggingface": ("devgen.providers.huggingface", "HuggingfaceProvider"),
    "ollama": ("devgen.providers.ollama", "OllamaProvider"),
}


def _provider_class(name: str) -> type[BaseProvider]:
    try:
        module_name, class_name = PROVIDERS[name.lower()]
    except KeyError as error:
        available = ", ".join(sorted(PROVIDERS))
        raise ValueError(
            f"Unknown provider `{name}`. Available providers: {available}."
        ) from error

    return getattr(import_module(module_name), class_name)


def generate_with_ai(
    prompt: str,
    provider: str = "gemini",
    api_key: str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> str:
    """Generate text with the requested provider.

    ``model=None`` lets the provider pick its own default model.
    """
    return _provider_class(provider)().generate(
        prompt,
        api_key=api_key,
        model=model,
        **kwargs,
    )


__all__ = ["PROVIDERS", "generate_with_ai"]
