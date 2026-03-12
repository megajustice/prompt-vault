import logging
from typing import Optional

from prompt_vault.providers.base import BaseProvider, ProviderResult, validate_model
from prompt_vault.providers.openai_provider import OpenAIProvider
from prompt_vault.providers.anthropic_provider import AnthropicProvider

logger = logging.getLogger("prompt_vault.providers")

_PROVIDERS = {
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
}


class ProviderError(Exception):
    """Raised for provider-level errors with helpful messages."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def list_providers() -> list:
    return list(_PROVIDERS.keys())


def get_provider(name: str) -> BaseProvider:
    provider = _PROVIDERS.get(name)
    if not provider:
        raise ProviderError(
            f"Unknown provider '{name}'. Supported: {list_providers()}"
        )
    return provider


def call_provider(provider_name: str, model: str, prompt: str) -> ProviderResult:
    """Central entry point: validate, call, return result."""
    provider = get_provider(provider_name)

    # Check for common model name mistakes
    warning = validate_model(provider_name, model)
    if warning:
        raise ProviderError(warning)

    try:
        return provider._timed_call(prompt, model)
    except ValueError as e:
        raise ProviderError(str(e), status_code=401)
    except RuntimeError as e:
        raise ProviderError(str(e), status_code=502)
