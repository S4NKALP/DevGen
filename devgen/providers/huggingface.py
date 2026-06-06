import requests

from devgen.providers.base import BaseProvider
from devgen.utils import format_token_limit_error, is_token_limit_error


class HuggingfaceProvider(BaseProvider):
    """Generates content using Hugging Face Inference API."""

    DISPLAY_NAME = "Hugging Face"
    API_URL_TEMPLATE = "https://api-inference.huggingface.co/models/{model}"
    DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

    def _generate(self, prompt, api_key, model, **kwargs):
        api_url = self.API_URL_TEMPLATE.format(model=model)
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 500, "return_full_text": False},
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
        except requests.HTTPError as e:
            if is_token_limit_error(e):
                raise RuntimeError(
                    format_token_limit_error(self.DISPLAY_NAME, e)
                ) from e
            status = e.response.status_code if e.response is not None else "?"
            raise RuntimeError(
                f"Hugging Face request failed (HTTP {status}): {e}. "
                "Check the model id and your token permissions."
            ) from e
        except requests.RequestException as e:
            raise RuntimeError(
                f"Hugging Face network error: {e}. Check your connection."
            ) from e

        if isinstance(result, list) and result and "generated_text" in result[0]:
            return result[0]["generated_text"]
        if isinstance(result, dict) and "error" in result:
            err = result["error"]
            if "is currently loading" in str(err).lower():
                raise RuntimeError(
                    f"Hugging Face model is loading: {err}. "
                    "Wait a minute and retry, or pick a different model."
                )
            raise RuntimeError(f"Hugging Face API error: {err}")
        raise RuntimeError(
            "Hugging Face returned an unexpected response shape. "
            "The model may not support text-generation."
        )
