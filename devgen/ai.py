from importlib import import_module


def generate_with_ai(
    prompt, provider="gemini", api_key=None, model="gemini-2.5-flash", **kwargs
):
    """Generates AI-based content such as commit messages using the specified provider and model.
    This function dynamically loads and initializes the provider class, sets the API key, and invokes the provider's generate method with the provided prompt and additional parameters.

    Args:
        prompt (str): The input prompt used to generate content.
        provider (str): The name of the provider module and class to use; defaults to "gemini".
        api_key (str, optional): The API key for authenticating with the provider. Should be provided via config file or kwargs.
        model (str): The name of the model to use with the provider; defaults to "gemini".
        **kwargs: Additional keyword arguments to pass to the provider's generate method.

    Returns:
        str: The generated content produced by the AI provider.
    """
    try:
        provider_module = import_module(f"devgen.providers.{provider}")
        class_name = "".join([x.capitalize() for x in provider.split("_")]) + "Provider"
        provider_class = getattr(provider_module, class_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(f"Provider `{provider}` not found or invalid: {e}") from e

    provider_instance = provider_class()
    return provider_instance.generate(prompt, api_key=api_key, model=model, **kwargs)
