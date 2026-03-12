import os
import time

from anthropic import Anthropic, APIError, AuthenticationError


def call_anthropic(prompt: str, model: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    client = Anthropic(api_key=api_key)

    start = time.perf_counter()
    try:
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
    except AuthenticationError:
        raise ValueError("Invalid ANTHROPIC_API_KEY")
    except APIError as e:
        raise RuntimeError(f"Anthropic API error: {e.message}")

    latency_ms = (time.perf_counter() - start) * 1000

    text = message.content[0].text if message.content else ""
    usage = message.usage

    return {
        "response": text,
        "provider": "anthropic",
        "model": model,
        "latency_ms": round(latency_ms, 2),
        "tokens": {
            "prompt": usage.input_tokens if usage else None,
            "completion": usage.output_tokens if usage else None,
            "total": (usage.input_tokens + usage.output_tokens) if usage else None,
        },
    }
