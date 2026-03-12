import os
import time
import logging
from typing import List

import httpx
from openai import OpenAI, APIError, APIConnectionError

from prompt_vault.providers.base import BaseProvider, ProviderResult

logger = logging.getLogger("prompt_vault.providers.lmstudio")

# Default LM Studio local server URL
DEFAULT_BASE_URL = "http://localhost:1234/v1"


def get_base_url() -> str:
    return os.environ.get("LMSTUDIO_BASE_URL", DEFAULT_BASE_URL)


def discover_models() -> List[str]:
    """Query the LM Studio /v1/models endpoint for loaded models."""
    base = get_base_url()
    try:
        resp = httpx.get(f"{base}/models", timeout=3.0)
        resp.raise_for_status()
        data = resp.json()
        models = [m["id"] for m in data.get("data", [])]
        logger.info("LM Studio: discovered %d models at %s", len(models), base)
        return models
    except Exception as e:
        logger.debug("LM Studio not reachable at %s: %s", base, e)
        return []


class LMStudioProvider(BaseProvider):
    name = "lmstudio"

    def _get_api_key(self) -> str:
        # LM Studio doesn't require a real API key
        return "lm-studio"

    def call(self, prompt: str, model: str) -> ProviderResult:
        base_url = get_base_url()
        client = OpenAI(
            api_key=self._get_api_key(),
            base_url=base_url,
        )

        start = time.perf_counter()
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
        except APIConnectionError:
            raise RuntimeError(
                f"Cannot connect to LM Studio at {base_url}. "
                "Is LM Studio running with the local server enabled?"
            )
        except APIError as e:
            raise RuntimeError(f"LM Studio API error: {e.message}")

        latency_ms = (time.perf_counter() - start) * 1000

        message = completion.choices[0].message.content or ""
        usage = completion.usage

        return ProviderResult(
            response=message,
            provider=self.name,
            model=model,
            latency_ms=round(latency_ms, 2),
            tokens={
                "prompt": usage.prompt_tokens if usage else None,
                "completion": usage.completion_tokens if usage else None,
                "total": usage.total_tokens if usage else None,
            },
        )
