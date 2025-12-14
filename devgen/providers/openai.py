from openai import OpenAI


class OpenaiProvider:
    """Generates a response string using the OpenAI ChatCompletion API based on the provided prompt and parameters. This method initializes an OpenAI client with the given API key, sends a chat completion request with specified model and additional parameters, and returns the content of the generated message.

    Args:
        prompt (str): The input prompt to generate a response for.
        api_key (str): The API key used to authenticate with the OpenAI service.
        model (str, optional): The model to use for generation; defaults to "gpt-4o".
        **kwargs: Additional keyword arguments to customize the API request (e.g., temperature).

    Returns:
        str: The content of the generated response message.
    """

    DEFAULT_MODEL = "gpt-4o"

    def generate(
        self, prompt: str, api_key: str, model: str | None = None, **kwargs
    ) -> str:
        """Generates a response from the OpenAI ChatCompletion API based on the provided prompt and parameters.

        Creates a client instance with the specified API key, sends a chat completion request using the selected model and additional parameters, and returns the generated message content as a string.

        Args:
            prompt (str): Prompt input.
            api_key (str): OpenAI API key.
            model (str, optional): Model to use (default: gpt-4o).
            **kwargs: Additional OpenAI ChatCompletion parameters (e.g., temperature).

        Returns:
            str: Generated response content.
        """
        # 1. Create a client instance with the API key.
        try:
            client = OpenAI(api_key=api_key)
        except Exception as e:
            # Add error handling if the client fails to initialize
            raise RuntimeError(f"Failed to initialize OpenAI client: {e}")

        # Remove debug from kwargs if present
        kwargs.pop("debug", None)

        # 2. Use the modern API syntax: client.chat.completions.create
        response = client.chat.completions.create(
            model=model or self.DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response.choices[0].message.content.strip()
