from typing import Any

from google import genai
from google.genai import types

from devgen.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    """Generates content using Google's Gemini models."""

    DISPLAY_NAME = "Gemini"
    DEFAULT_MODEL = "gemini-2.5-flash"

    def _generate(
        self,
        prompt: str,
        api_key: str | None,
        model: str,
        **kwargs: Any,
    ) -> str:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=kwargs.get("temperature", 0.7),
                top_p=kwargs.get("top_p", 0.95),
                top_k=kwargs.get("top_k", 40),
                max_output_tokens=kwargs.get("max_output_tokens", 2048),
            ),
        )
        return response.text or ""
