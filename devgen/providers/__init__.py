def get_provider(name):
    name_lower = name.lower()
    if name_lower == "gemini":
        from devgen.providers.gemini import GeminiProvider

        return GeminiProvider()
    elif name_lower == "openai":
        from devgen.providers.openai import OpenaiProvider

        return OpenaiProvider()
    elif name_lower == "huggingface":
        from devgen.providers.huggingface import HuggingfaceProvider

        return HuggingfaceProvider()
    elif name_lower == "openrouter":
        from devgen.providers.openrouter import OpenrouterProvider

        return OpenrouterProvider()
    elif name_lower == "anthropic":
        from devgen.providers.anthropic import AnthropicProvider

        return AnthropicProvider()

    raise NotImplementedError(f"Provider '{name}' is not implemented yet.")
