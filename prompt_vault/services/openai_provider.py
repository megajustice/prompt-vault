import os
import time

from openai import OpenAI, APIError, AuthenticationError


def call_openai(prompt: str, model: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    client = OpenAI(api_key=api_key)

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

    return {
        "response": message,
        "provider": "openai",
        "model": model,
        "latency_ms": round(latency_ms, 2),
        "tokens": {
            "prompt": usage.prompt_tokens if usage else None,
            "completion": usage.completion_tokens if usage else None,
            "total": usage.total_tokens if usage else None,
        },
    }
