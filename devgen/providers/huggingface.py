from typing import Any

import requests

from devgen.providers.base import BaseProvider


class HuggingfaceProvider(BaseProvider):
    """Generates content using the Hugging Face Inference API."""

    DISPLAY_NAME = "Hugging Face"
    API_URL_TEMPLATE = "https://api-inference.huggingface.co/models/{model}"
    DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

    def _generate(
        self,
        prompt: str,
        api_key: str | None,
        model: str,
        **kwargs: Any,
    ) -> str:
        try:
            response = requests.post(
                self.API_URL_TEMPLATE.format(model=model),
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": kwargs.get("max_new_tokens", 500),
                        "return_full_text": False,
                    },
                },
                timeout=kwargs.get("timeout", 120),
            )
            response.raise_for_status()
        except requests.HTTPError as error:
            status = error.response.status_code if error.response else "?"
            raise RuntimeError(
                f"Hugging Face request failed (HTTP {status}): {error}. "
                "Check the model id and your token permissions."
            ) from error
        except requests.RequestException as error:
            raise RuntimeError(
                f"Hugging Face network error: {error}. Check your connection."
            ) from error

        result = response.json()

        if isinstance(result, list) and result and "generated_text" in result[0]:
            return result[0]["generated_text"]

        if isinstance(result, dict) and "error" in result:
            error = result["error"]
            if "is currently loading" in str(error).lower():
                raise RuntimeError(
                    f"Hugging Face model is loading: {error}. "
                    "Wait a minute and retry, or pick a different model."
                )
            raise RuntimeError(f"Hugging Face API error: {error}")

        raise RuntimeError(
            "Hugging Face returned an unexpected response shape. "
            "The model may not support text-generation."
        )
