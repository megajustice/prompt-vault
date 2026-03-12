import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("prompt_vault.providers")


@dataclass
class ProviderResult:
    """Consistent result type returned by all providers."""

    response: str
    provider: str
    model: str
    latency_ms: float
    tokens: dict = field(default_factory=lambda: {
        "prompt": None, "completion": None, "total": None,
    })


class BaseProvider:
    """Base class for LLM providers."""

    name: str = ""

    def _get_api_key(self) -> str:
        raise NotImplementedError

    def call(self, prompt: str, model: str) -> ProviderResult:
        raise NotImplementedError

    def _timed_call(self, prompt: str, model: str) -> ProviderResult:
        """Wrapper that measures latency and logs the call."""
        logger.info("Calling %s model=%s prompt_len=%d", self.name, model, len(prompt))
        start = time.perf_counter()
        try:
            result = self.call(prompt, model)
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(
                "Provider %s model=%s failed after %.0fms",
                self.name, model, elapsed, exc_info=True,
            )
            raise
        logger.info(
            "Provider %s model=%s completed in %.0fms tokens=%s",
            self.name, model, result.latency_ms,
            result.tokens.get("total"),
        )
        return result


# Known model IDs per provider for validation hints
KNOWN_MODELS = {
    "openai": [
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
    ],
    "anthropic": [
        "claude-opus-4-6", "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ],
}

# Common wrong names → suggestion
MODEL_SUGGESTIONS = {
    "claude-3-7-sonnet": "claude-sonnet-4-6",
    "claude-3-sonnet": "claude-sonnet-4-6",
    "claude-3-opus": "claude-opus-4-6",
    "claude-3-haiku": "claude-haiku-4-5-20251001",
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-opus": "claude-opus-4-6",
    "claude-haiku": "claude-haiku-4-5-20251001",
    "gpt4": "gpt-4o",
    "gpt4o": "gpt-4o",
    "gpt-4o-latest": "gpt-4o",
}


def validate_model(provider: str, model: str) -> Optional[str]:
    """Return a warning string if the model looks wrong, else None."""
    if model in MODEL_SUGGESTIONS:
        return (
            f"Unknown model '{model}'. "
            f"Did you mean '{MODEL_SUGGESTIONS[model]}'?"
        )
    return None
