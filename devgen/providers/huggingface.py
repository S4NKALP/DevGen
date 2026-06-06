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
            raise ValueError(
                "Hugging Face API token is missing. "
                "Set it via `devgen setup config` or pass --api-key."
            )

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

            if isinstance(result, list) and result and "generated_text" in result[0]:
                return result[0]["generated_text"].strip()
            elif isinstance(result, dict) and "error" in result:
                err = result["error"]
                if "is currently loading" in str(err).lower():
                    raise RuntimeError(
                        f"Hugging Face model is loading: {err}. "
                        "Wait a minute and retry, or pick a different model."
                    )
                raise RuntimeError(f"Hugging Face API error: {err}")
            else:
                raise RuntimeError(
                    "Hugging Face returned an unexpected response shape. "
                    "The model may not support text-generation."
                )

        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            raise RuntimeError(
                f"Hugging Face request failed (HTTP {status}): {e}. "
                "Check the model id and your token permissions."
            ) from e
        except requests.RequestException as e:
            raise RuntimeError(
                f"Hugging Face network error: {e}. Check your connection."
            ) from e
        except Exception as e:
            raise RuntimeError(f"Hugging Face generation failed: {e}") from e
