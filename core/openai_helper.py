"""
OpenAI API Helper — Model-aware API call wrapper.
Handles parameter compatibility across different model families.
"""

from openai import OpenAI
from core.retry_config import retry_openai_call


def create_chat_completion(
    client: OpenAI,
    model: str,
    messages: list,
    temperature: float = 0,
    max_output_tokens: int = 4096,
    response_format: dict = None,
    **kwargs
):
    """
    Model-aware wrapper for OpenAI chat completions.
    
    Automatically selects correct parameters based on model family:
    - Newer models (gpt-5.x, o1-series): use max_completion_tokens
    - Legacy models (gpt-4o, gpt-4-turbo, etc.): use max_tokens
    - O1-series models: exclude temperature parameter (not supported)
    
    Args:
        client: OpenAI client instance
        model: Model name (e.g., "gpt-4o", "gpt-5.2", "o1-preview")
        messages: List of message dicts for the conversation
        temperature: Sampling temperature (ignored for o1-series)
        max_output_tokens: Maximum tokens to generate (unified parameter name)
        response_format: Optional response format specification
        **kwargs: Additional parameters to pass to the API
    
    Returns:
        OpenAI ChatCompletion response object
    """
    
    # Detect model family and build appropriate parameters
    params = {
        "model": model,
        "messages": messages,
        **kwargs
    }
    
    # Check if it's an o1-series model (reasoning models)
    is_o1_series = model.startswith("o1-") or model.startswith("o1")
    
    # Check if it's a newer model that uses max_completion_tokens
    is_newer_model = (
        model.startswith("gpt-5") or 
        model.startswith("gpt-6") or
        is_o1_series
    )
    
    # Add temperature (unless it's o1-series which doesn't support it)
    if not is_o1_series:
        params["temperature"] = temperature
    
    # Add max tokens parameter (name depends on model family)
    if is_newer_model:
        params["max_completion_tokens"] = max_output_tokens
    else:
        params["max_tokens"] = max_output_tokens
    
    # Add response format if specified
    if response_format:
        params["response_format"] = response_format
    
    # Wrap API call with retry logic
    @retry_openai_call
    def _call_openai():
        return client.chat.completions.create(**params)
    
    return _call_openai()
