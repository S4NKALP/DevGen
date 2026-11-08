"""Base class for AI providers.

Every provider implements :meth:`_generate` and inherits API-key
validation, retry-with-backoff on quota errors, and consistent error
translation from :class:`BaseProvider`.
"""

import time
from abc import ABC, abstractmethod
from typing import Any

from devgen.utils import format_token_limit_error, is_token_limit_error

# Keyword arguments owned by DevGen — never forwarded to provider SDKs.
DEVGEN_ONLY_KWARGS = frozenset({"debug", "ollama_host", "max_retries", "retry_delay"})

_QUOTA_MARKERS = (
    "429",
    "RESOURCE_EXHAUSTED",
    "QUOTA_EXCEEDED",
    "THROTTLED",
    "RATE_LIMIT_EXCEEDED",
    "TOO_MANY_REQUESTS",
)


class BaseProvider(ABC):
    """Abstract base for all AI providers."""

    #: Human-readable name used in error messages.
    DISPLAY_NAME: str = ""
    #: Whether the provider requires an API key.
    REQUIRES_API_KEY: bool = True
    #: Default model id when the user doesn't specify one.
    DEFAULT_MODEL: str = ""
    #: Appended to generic request failures.
    ERROR_HINT: str = (
        "Check the model name, API key permissions, and your account quota."
    )

    def generate(
        self,
        prompt: str,
        api_key: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Validate input, call the provider, and retry transient quota errors."""
        if self.REQUIRES_API_KEY and not api_key:
            raise ValueError(
                f"{self.DISPLAY_NAME} API key is missing. "
                "Set it via `devgen setup config` or pass --api-key."
            )

        chosen_model = model or self.DEFAULT_MODEL
        max_retries = kwargs.get("max_retries", 5)
        retry_delay = kwargs.get("retry_delay", 10)

        for attempt in range(max_retries + 1):
            try:
                return (
                    self._generate(prompt, api_key, chosen_model, **kwargs) or ""
                ).strip()
            except Exception as error:
                if not self._is_quota_error(error):
                    self._handle_error(error)

                if attempt >= max_retries:
                    raise RuntimeError(
                        f"{self.DISPLAY_NAME} API quota exhausted (429) "
                        "after multiple retries."
                    ) from error

                delay = retry_delay * (2**attempt)
                print(
                    f"\n[{self.DISPLAY_NAME}] Quota/rate limit hit. "
                    f"Waiting {delay}s and retrying "
                    f"(attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(delay)

        return ""  # Unreachable; keeps type checkers happy if _handle_error changes.

    @staticmethod
    def _is_quota_error(error: Exception) -> bool:
        # Token-limit errors can mention numbers that look like HTTP 429s;
        # handle them as context overflows instead of retrying.
        if is_token_limit_error(error):
            return False
        text = str(error).upper()
        return any(marker in text for marker in _QUOTA_MARKERS)

    @staticmethod
    def _sdk_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
        """Drop DevGen-only keyword arguments before calling an SDK."""
        return {
            key: value for key, value in kwargs.items() if key not in DEVGEN_ONLY_KWARGS
        }

    def _handle_error(self, error: Exception) -> None:
        """Translate any provider exception into a user-facing RuntimeError."""
        if is_token_limit_error(error):
            raise RuntimeError(
                format_token_limit_error(self.DISPLAY_NAME, error)
            ) from error

        raise RuntimeError(
            f"{self.DISPLAY_NAME} request failed: {error}. {self.ERROR_HINT}"
        ) from error

    @abstractmethod
    def _generate(
        self,
        prompt: str,
        api_key: str | None,
        model: str,
        **kwargs: Any,
    ) -> str:
        """Provider-specific generation. Return the raw generated text."""
        raise NotImplementedError
