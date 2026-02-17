"""
Model Switcher — allows easy swapping between OpenAI models.
Supports CLI override via --model flag.
"""

import sys
import config


def get_model(override: str = None) -> str:
    """
    Returns the model to use, in priority order:
    1. Explicit override parameter
    2. --model CLI argument
    3. DEFAULT_MODEL from .env / config
    """
    if override:
        return override

    # Check CLI args for --model flag
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--model" and i + 1 < len(args):
            model = args[i + 1]
            if model in config.AVAILABLE_MODELS:
                return model
            else:
                print(f"⚠ Warning: '{model}' not in ranked models. Using anyway.")
                return model

    return config.DEFAULT_MODEL


def list_models() -> list:
    """Returns ranked list of available models."""
    return config.AVAILABLE_MODELS


if __name__ == "__main__":
    print(f"Current model: {get_model()}")
    print(f"Available models: {list_models()}")
