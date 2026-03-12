import os
import time

from openai import OpenAI, APIError, AuthenticationError

from prompt_vault.providers.base import BaseProvider, ProviderResult


class OpenAIProvider(BaseProvider):
    name = "openai"

    def _get_api_key(self) -> str:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        return key

    def call(self, prompt: str, model: str) -> ProviderResult:
        client = OpenAI(api_key=self._get_api_key())

        start = time.perf_counter()
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
        except AuthenticationError:
            raise ValueError("Invalid OPENAI_API_KEY")
        except APIError as e:
            raise RuntimeError(f"OpenAI API error: {e.message}")

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
