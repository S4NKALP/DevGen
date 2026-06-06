import time

from google import genai
from google.genai import types

from devgen.providers.base import BaseProvider
from devgen.utils import is_token_limit_error


class GeminiProvider(BaseProvider):
    """Generates content using Google's Gemini models."""

    DISPLAY_NAME = "Gemini"
    DEFAULT_MODEL = "gemini-2.5-flash"

    def _generate(self, prompt, api_key, model, **kwargs):
        max_retries = kwargs.get("max_retries", 5)
        base_delay = kwargs.get("retry_delay", 10)  # 10s base for 429 backoff
        client = genai.Client(api_key=api_key)

        for attempt in range(max_retries + 1):
            try:
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
                return response.text
            except Exception as e:
                if is_token_limit_error(e):
                    raise  # base class handles with friendly message
                if self._is_quota_error(e) and attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    print(
                        f"\n[Gemini] Quota limit hit (429). This is often a temporary "
                        f"rate limit (RPM). Waiting {delay}s and retrying... "
                        f"(Attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    continue
                if self._is_quota_error(e):
                    raise RuntimeError(
                        "Gemini API quota exhausted (429) after multiple retries.\n\n"
                        "POSSIBLE CAUSES:\n"
                        "1. Rate Limit (RPM/RPD): You are sending requests too fast for the Free Tier.\n"
                        "2. Daily Limit: You have reached the maximum free requests allowed for today (typically 1,500).\n"
                        "3. Credit/Billing: If on a paid plan, your credit may be exhausted.\n\n"
                        "Please check your usage metrics at: https://aistudio.google.com/app/usage"
                    ) from e
                raise

    @staticmethod
    def _is_quota_error(error: Exception) -> bool:
        text = str(error).upper()
        return any(
            marker in text
            for marker in ("429", "RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED", "THROTTLED")
        )
