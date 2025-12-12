import google.generativeai as genai


class GeminiProvider:
    """Generates content using Google's Gemini models."""

    def generate(
        self, prompt: str, api_key: str, model: str = "gemini-pro", **kwargs
    ) -> str:
        """Generates a response using the Gemini API."""
        if not api_key:
            raise ValueError("Gemini API key is required.")

        genai.configure(api_key=api_key)

        # Handle model name mapping if needed, or trust user input
        # gemini-pro is a common default

        try:
            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {e}")
