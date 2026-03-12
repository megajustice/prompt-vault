# Prompt Vault

A local-first LLM gateway and prompt observability tool. Route prompts to OpenAI or Anthropic, log every request automatically, compare models side-by-side, replay past prompts, and browse everything through a built-in dashboard.

Prompt Vault is built for developers who work across multiple LLM providers and want a single place to see what they sent, what came back, how long it took, and how much it cost — without sending their data to a third-party service.

**This is a local tool.** It runs on your machine, stores data in SQLite, and talks directly to provider APIs using your own keys.

---

## Features

**Gateway**
- Send prompts to OpenAI and Anthropic through a unified API
- Every request is automatically logged with latency, token counts, and status
- Model name validation with suggestions for common mistakes

**OpenAI-Compatible Endpoint**
- Drop-in `/v1/chat/completions` endpoint that works with existing OpenAI client libraries
- Route to any provider using `provider/model` syntax in the model field
- Returns proper OpenAI-format error responses

**Compare**
- Send one prompt to multiple models in a single request
- Side-by-side results with per-model latency
- Browser-based comparison page or use the API directly

**Replay**
- Re-run any past prompt against the same or a different model
- Replays are linked to the original log entry for tracking

**Observability**
- Dashboard with stat cards, provider breakdowns, and latency charts
- Per-request tracking: status, error messages, prompt/completion/total tokens
- Daily volume chart, model-level latency averages
- Full-text search across prompts, responses, models, providers, and tags

**Export**
- Download prompt history as JSON, CSV, or Markdown
- All fields included: prompt, response, tokens, latency, tags, timestamps

**Tags**
- Add and edit comma-separated tags on any log entry
- Filter the prompt list by tag

---

## Architecture

```
prompt-vault/
├── run.py                         # uvicorn entry point
├── prompt_vault/
│   ├── main.py                    # FastAPI app, router registration, startup
│   ├── config.py                  # .env loading, paths, database URL
│   ├── database.py                # SQLite engine via SQLModel
│   ├── models.py                  # PromptLog table + PromptLogCreate schema
│   ├── migrate.py                 # Idempotent SQLite column migrations
│   ├── providers/
│   │   ├── base.py                # BaseProvider, ProviderResult, model validation
│   │   ├── openai_provider.py     # OpenAI chat completions
│   │   ├── anthropic_provider.py  # Anthropic messages API
│   │   └── registry.py            # Provider lookup, call_provider(), ProviderError
│   ├── routes/
│   │   ├── api.py                 # CRUD, stats, filters
│   │   ├── gateway.py             # /api/ask, /api/compare, /api/replay, export, tags
│   │   ├── openai_compat.py       # /v1/chat/completions
│   │   └── ui.py                  # Dashboard, prompts, detail, compare, stats pages
│   ├── services/
│   │   ├── prompt_service.py      # Query logic, stats aggregations
│   │   └── json_logger.py         # Append-only JSONL writer
│   ├── templates/                 # Jinja2 + HTMX server-rendered pages
│   └── static/                    # CSS (dark theme)
└── logs/                          # JSONL log output
```

**Stack:** Python 3.9+, FastAPI, SQLite, SQLModel, HTMX 2.0, Jinja2

**Data storage:** SQLite database (`prompt_vault.db`) + append-only JSONL file (`logs/prompts.jsonl`). Both are local. Nothing leaves your machine except API calls to the providers you configure.

---

## Endpoints

### Gateway

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/ask` | Send a prompt to a provider and model |
| `POST` | `/api/compare` | Send one prompt to multiple models |
| `POST` | `/api/replay` | Re-run a past prompt (same or different model) |

### OpenAI-Compatible

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/chat/completions` | OpenAI-format chat completions |

### Data

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/logs` | Manually log a prompt/response pair |
| `GET` | `/api/logs` | List logs (filters: `provider`, `model`, `status`, `tag`, `skip`, `limit`) |
| `GET` | `/api/logs/search?q=term` | Full-text search |
| `GET` | `/api/logs/{id}` | Get a single log entry |
| `PATCH` | `/api/logs/{id}/tags` | Update tags on a log entry |
| `GET` | `/api/stats` | Aggregated stats (counts, latency, tokens, daily volume) |
| `GET` | `/api/filters` | Distinct providers and models in the database |
| `GET` | `/api/export?format=json` | Export logs (`json`, `csv`, or `markdown`) |

### UI Pages

| Path | Page |
|------|------|
| `/` | Dashboard — stats, charts, recent prompts |
| `/prompts` | Prompt list — search, filters, pagination |
| `/prompts/{id}` | Detail — copy, replay, tag editing, replay chain |
| `/compare` | Side-by-side model comparison form |
| `/stats` | Analytics — latency by model, volume, token totals |

---

## Model Naming

### Direct API (`/api/ask`, `/api/compare`, `/api/replay`)

Specify `provider` and `model` as separate fields:

```json
{
  "provider": "openai",
  "model": "gpt-4o"
}
```

### OpenAI-Compatible (`/v1/chat/completions`)

Use `provider/model` in the model field. Bare model names default to OpenAI:

| You send | Provider | Model |
|----------|----------|-------|
| `gpt-4o` | openai | gpt-4o |
| `anthropic/claude-sonnet-4-6` | anthropic | claude-sonnet-4-6 |
| `openai/gpt-4o-mini` | openai | gpt-4o-mini |

### Validated Models

**OpenAI:** `gpt-4o` · `gpt-4o-mini` · `gpt-4-turbo` · `gpt-4` · `gpt-3.5-turbo`

**Anthropic:** `claude-opus-4-6` · `claude-sonnet-4-6` · `claude-haiku-4-5-20251001`

Common mistakes are caught with suggestions:

| You typed | Suggestion |
|-----------|-----------|
| `claude-3-7-sonnet` | `claude-sonnet-4-6` |
| `gpt4o` | `gpt-4o` |
| `claude-sonnet` | `claude-sonnet-4-6` |

Model names not in the validation list are passed through to the provider as-is.

---

## Setup

```bash
git clone https://github.com/megajustice/prompt-vault.git
cd prompt-vault
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

Both keys are optional. You only need the key for providers you plan to use.

Start the server:

```bash
python run.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## Examples

**Send a prompt:**

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "prompt": "What is a monad in three sentences?"
  }'
```

**Compare two models:**

```bash
curl -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain recursion to a five-year-old.",
    "models": [
      {"provider": "openai", "model": "gpt-4o"},
      {"provider": "anthropic", "model": "claude-sonnet-4-6"}
    ]
  }'
```

**OpenAI-compatible endpoint:**

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-sonnet-4-6",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Replay a prompt on a different model:**

```bash
curl -X POST http://localhost:8000/api/replay \
  -H "Content-Type: application/json" \
  -d '{"log_id": 1, "provider": "anthropic", "model": "claude-sonnet-4-6"}'
```

**Export as CSV:**

```bash
curl http://localhost:8000/api/export?format=csv -o prompts.csv
```

**Update tags:**

```bash
curl -X PATCH http://localhost:8000/api/logs/1/tags \
  -H "Content-Type: application/json" \
  -d '{"tags": "production,important"}'
```

**Get stats:**

```bash
curl http://localhost:8000/api/stats | python -m json.tool
```

---

## Screenshots

<!-- Replace placeholders with actual screenshots -->

| Page | Screenshot |
|------|-----------|
| Dashboard | ![Dashboard](docs/screenshots/dashboard.png) |
| Prompts | ![Prompts](docs/screenshots/prompts.png) |
| Detail | ![Detail](docs/screenshots/detail.png) |
| Compare | ![Compare](docs/screenshots/compare.png) |
| Stats | ![Stats](docs/screenshots/stats.png) |

---

## Roadmap

Prompt Vault is the logging and observation layer. The longer-term direction is toward **context management** — not just tracking what was sent to an LLM, but building reusable context libraries that improve prompt quality over time.

**Near-term**
- Prompt templates with variable substitution
- Cost estimation per request using model-specific pricing
- Streaming support for the OpenAI-compatible endpoint
- Additional providers: Google Gemini, local models via Ollama
- Webhook notifications on error or latency threshold

**Medium-term**
- Prompt chains — link sequential prompts into tracked workflows
- A/B prompt testing with statistical comparison
- Context fragments — save and reuse system prompts, few-shot examples, reference material
- Version-controlled prompt library

**Longer-term (ContentLibrary direction)**
- Structured context store that pairs prompts with domain-specific source material
- Retrieval layer that surfaces relevant past prompts and responses when composing new ones
- Cross-session context memory — learn which context patterns produce better results per model
- Integration with document stores and knowledge bases for grounded prompt construction

---

## Design Decisions

**SQLite, not Postgres.** This is a local developer tool. SQLite is zero-config, fast, and the database file is trivial to back up or move.

**HTMX, not React.** Server-rendered with partial updates. No build step, no node_modules, no JavaScript framework to maintain.

**Append-only JSONL log.** The database is the primary store. The JSONL file is a portable backup that survives database issues and pipes easily into other tools.

**Provider abstraction.** Adding a new provider means implementing one class with a `call()` method. The registry, logging, and validation are shared.

**No auth.** This runs on localhost. If you need auth, put it behind a reverse proxy.

---

## License

MIT — Christopher Justice
