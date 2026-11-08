from devgen.providers.openai_compatible import OpenAICompatibleProvider


class OpenaiProvider(OpenAICompatibleProvider):
    """Generates content using OpenAI's Chat Completions API."""

    DISPLAY_NAME = "OpenAI"
    DEFAULT_MODEL = "gpt-4o"
