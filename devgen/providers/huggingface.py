import requests


class HuggingfaceProvider:
    """Generates content using Hugging Face Inference API."""

    API_URL_TEMPLATE = "https://api-inference.huggingface.co/models/{model}"

    def generate(
        self,
        prompt: str,
        api_key: str,
        model: str = "mistralai/Mistral-7B-Instruct-v0.2",
        **kwargs,
    ) -> str:
        """Generates a response using Hugging Face API."""
        if not api_key:
            raise ValueError("Hugging Face API token is required.")

        api_url = self.API_URL_TEMPLATE.format(model=model)
        headers = {"Authorization": f"Bearer {api_key}"}

        # HF models often expect specific prompting formats, but we'll send raw prompt
        # Some models are text-generation, some are conversational.
        # Assuming text-generation for generic usage.

        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 500, "return_full_text": False},
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            if isinstance(result, list) and "generated_text" in result[0]:
                return result[0]["generated_text"].strip()
            elif isinstance(result, dict) and "error" in result:
                raise RuntimeError(f"Hugging Face API error: {result['error']}")
            else:
                return str(result)

        except Exception as e:
            raise RuntimeError(f"Hugging Face generation failed: {e}")
