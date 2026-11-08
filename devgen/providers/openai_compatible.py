"""Shared implementation for providers with an OpenAI-compatible API."""

from typing import Any, ClassVar

from openai import OpenAI

from devgen.providers.base import BaseProvider


class OpenAICompatibleProvider(BaseProvider):
    """Base class for OpenAI, OpenRouter, and Ollama.

    Subclasses only need to set the display name, default model, and
    optionally override :meth:`_client` for a custom endpoint.
    """

    BASE_URL: ClassVar[str | None] = None
    DEFAULT_HEADERS: ClassVar[dict[str, str] | None] = None

    def _client(self, api_key: str | None, **kwargs: Any) -> OpenAI:
        options: dict[str, Any] = {"api_key": api_key or "not-needed"}
        if self.BASE_URL:
            options["base_url"] = self.BASE_URL
        if self.DEFAULT_HEADERS:
            options["default_headers"] = self.DEFAULT_HEADERS
        return OpenAI(**options)

    def _generate(
        self,
        prompt: str,
        api_key: str | None,
        model: str,
        **kwargs: Any,
    ) -> str:
        with self._client(api_key, **kwargs) as client:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **self._sdk_kwargs(kwargs),
            )

        if not response.choices:
            raise RuntimeError(
                f"{self.DISPLAY_NAME} returned no choices for model {model!r}."
            )
        return response.choices[0].message.content or ""
