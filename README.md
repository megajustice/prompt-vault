# Prompt Vault

Track prompts and responses across multiple LLM providers. Store everything in SQLite, browse with a local HTMX UI, and log to JSON for portability.

## Quick Start

```bash
pip install -r requirements.txt
python run.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Log a Prompt

```bash
curl -X POST http://127.0.0.1:8000/api/logs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing",
    "response": "Quantum computing uses qubits...",
    "model": "gpt-4",
    "provider": "openai",
    "latency_ms": 1230.5,
    "tags": "science,explainer"
  }'
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/logs` | Log a prompt/response |
| GET | `/api/logs` | List logs (query: `skip`, `limit`) |
| GET | `/api/logs/search?q=term` | Search logs |
| GET | `/api/logs/{id}` | Get single log |

## Stack

- **Python** + **FastAPI** - API and server
- **SQLite** + **SQLModel** - Storage and ORM
- **HTMX** + **Jinja2** - Server-rendered UI with live search
- **JSON Lines** - Append-only log file at `logs/prompts.jsonl`

## Project Structure

```
prompt-vault/
├── run.py                  # Entry point
├── prompt_vault/
│   ├── main.py             # FastAPI app
│   ├── config.py           # Settings
│   ├── database.py         # SQLite engine
│   ├── models.py           # SQLModel schemas
│   ├── routes/
│   │   ├── api.py          # REST API
│   │   └── ui.py           # HTMX pages
│   ├── services/
│   │   ├── prompt_service.py  # Business logic
│   │   └── json_logger.py     # JSONL writer
│   ├── templates/          # Jinja2 HTML
│   └── static/             # CSS
└── logs/                   # JSON log output
```

## License

MIT
