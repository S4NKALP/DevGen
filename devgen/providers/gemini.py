import time
from google import genai
from google.genai import types


class GeminiProvider:
    """Generates content using Google's Gemini models."""

    def generate(
        self, prompt: str, api_key: str, model: str = "gemini-2.5-flash", **kwargs
    ) -> str:
        """Generates a response using the Gemini API.

        Default model is updated to gemini-2.5-flash which is the latest
        recommended model.
        """
        if not api_key:
            raise ValueError("Gemini API key is required.")

        client = genai.Client(api_key=api_key)

        max_retries = kwargs.get("max_retries", 5)
        base_delay = kwargs.get("retry_delay", 10)  # 10 seconds base delay for 429

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
                return response.text.strip()
            except Exception as e:
                error_msg = str(e).upper()
                # Check for 429 or ResourceExhausted in common error formats
                if any(x in error_msg for x in ["429", "RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED", "THROTTLED"]):
                    if attempt < max_retries:
                        delay = base_delay * (2**attempt)
                        print(
                            f"\n[Gemini] Quota limit hit (429). This is often a temporary rate limit (RPM). "
                            f"Waiting {delay}s and retrying... (Attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        raise RuntimeError(
                            "Gemini API quota exhausted (429) after multiple retries.\n\n"
                            "POSSIBLE CAUSES:\n"
                            "1. Rate Limit (RPM/RPD): You are sending requests too fast for the Free Tier.\n"
                            "2. Daily Limit: You have reached the maximum free requests allowed for today (typically 1,500).\n"
                            "3. Credit/Billing: If on a paid plan, your credit may be exhausted.\n\n"
                            "Please check your usage metrics at: https://aistudio.google.com/app/usage"
                        ) from e
                raise RuntimeError(f"Gemini generation failed: {e}") from e
