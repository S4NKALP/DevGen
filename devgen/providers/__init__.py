from devgen.providers.anthropic import AnthropicProvider
from devgen.providers.gemini import GeminiProvider
from devgen.providers.huggingface import HuggingfaceProvider
from devgen.providers.openai import OpenaiProvider
from devgen.providers.openrouter import OpenrouterProvider


def get_provider(name):
    name_lower = name.lower()
    if name_lower == "gemini":
        return GeminiProvider()
    elif name_lower == "openai":
        return OpenaiProvider()
    elif name_lower == "huggingface":
        return HuggingfaceProvider()
    elif name_lower == "openrouter":
        return OpenrouterProvider()
    elif name_lower == "anthropic":
        return AnthropicProvider()

    raise NotImplementedError(f"Provider '{name}' is not implemented yet.")
