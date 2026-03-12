import json
from datetime import timezone

from prompt_vault.config import LOG_FILE
from prompt_vault.models import PromptLog


def write_log_entry(entry: PromptLog) -> None:
    record = {
        "id": entry.id,
        "prompt": entry.prompt,
        "response": entry.response,
        "model": entry.model,
        "provider": entry.provider,
        "latency_ms": entry.latency_ms,
        "tags": entry.tags,
        "created_at": entry.created_at.replace(tzinfo=timezone.utc).isoformat(),
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")
