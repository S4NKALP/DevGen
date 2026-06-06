"""Base class for AI providers.

Every provider implements :meth:`_generate` and inherits the standard
contract: API-key validation, token-limit detection, and friendly
RuntimeError wrapping. Providers with provider-specific error shapes
(eg. Hugging Face's HTTPError / RequestException split) override
:meth:`_handle_error`.
"""

from abc import ABC, abstractmethod
from typing import Any

from devgen.utils import format_token_limit_error, is_token_limit_error


class BaseProvider(ABC):
    """Abstract base for all AI providers."""

    #: Human-readable name used in error messages.
    DISPLAY_NAME: str = ""
    #: Whether the provider requires an API key.
    REQUIRES_API_KEY: bool = True
    #: Default model id when the user doesn't specify one.
    DEFAULT_MODEL: str = ""

    def generate(
        self,
        prompt: str,
        api_key: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Public entry point. Validates input, dispatches, and wraps errors.

        Args:
            prompt: The prompt to send to the model.
            api_key: Provider API key. May be ``None`` for local providers
                (see :attr:`REQUIRES_API_KEY`).
            model: Model id. Falls back to :attr:`DEFAULT_MODEL` when ``None``.
            **kwargs: Forwarded to :meth:`_generate`.

        Returns:
            The generated text, stripped.

        Raises:
            ValueError: If the provider requires an API key and none was given.
            RuntimeError: For any underlying failure, with a friendly message.
        """
        if self.REQUIRES_API_KEY and not api_key:
            raise ValueError(
                f"{self.DISPLAY_NAME} API key is missing. "
                "Set it via `devgen setup config` or pass --api-key."
            )
        chosen_model = model or self.DEFAULT_MODEL
        try:
            return self._generate(prompt, api_key, chosen_model, **kwargs).strip()
        except Exception as e:
            self._handle_error(e)

    def _handle_error(self, error: Exception) -> None:
        """Translate an internal exception into a user-facing RuntimeError.

        Token-limit / context-window errors are reformatted with
        :func:`format_token_limit_error`; everything else is wrapped in a
        generic provider message. Subclasses override this to add
        provider-specific error shapes (eg. HTTPError vs RequestException).
        """
        if is_token_limit_error(error):
            raise RuntimeError(
                format_token_limit_error(self.DISPLAY_NAME, error)
            ) from error
        raise RuntimeError(
            f"{self.DISPLAY_NAME} request failed: {error}. "
            "Check the model name, API key permissions, and your account quota."
        ) from error

    @abstractmethod
    def _generate(
        self,
        prompt: str,
        api_key: str | None,
        model: str,
        **kwargs: Any,
    ) -> str:
        """Provider-specific generation. Return the raw generated text.

        Implementations may raise any exception; :meth:`_handle_error` will
        translate it. Re-raise an exception to defer to default handling.
        """
        raise NotImplementedError
