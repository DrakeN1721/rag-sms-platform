# RAG SMS Lead Nurturing Platform (MVP)

Production-ready MVP for real-estate lead nurturing over SMS with retrieval-augmented generation.

## Architecture

```text
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  Twilio SMS │───▶│  FastAPI App │───▶│   Qdrant    │
│  Webhooks   │◀───│    (async)   │◀───│  Vector DB  │
└─────────────┘    └──────┬───────┘    └─────────────┘
                          │
                   ┌──────┴───────┐
                   │              │
              ┌────▼────┐  ┌─────▼──────┐
              │  Redis   │  │  LLM API   │
              │ Queue +  │  │ Claude /   │
              │  State   │  │ OpenAI     │
              └─────────┘  └────────────┘
```

## Features

- Async FastAPI service with Twilio webhook handling
- RAG pipeline: chunking, embeddings, Qdrant storage, hybrid retrieval, reranking
- Multi-tenant-aware data model (agency partitioning)
- Redis-backed conversation state machine
- Unified LLM client (OpenAI + Anthropic fallback)
- GoHighLevel CRM sync integration
- Campaign scheduler + trigger + A/B testing modules
- Background workers for embeddings, CRM sync, campaign dispatch
- Unit tests for RAG, intent classifier, and conversation state transitions

## Project Layout

- `core/`: settings, pydantic models, SQLAlchemy async models
- `rag/`: ingestion, vector store, retrieval and reranking
- `llm/`: prompts, provider client, structured parsing, evaluator
- `messaging/`: Twilio integration + routing + conversation state
- `crm/`: GoHighLevel client and sync service
- `campaign/`: scheduler, triggers, A/B testing
- `intelligence/`: intent, propensity, next-best-action
- `api/`: app entrypoint, middleware, REST routes
- `workers/`: Redis queue workers
- `scripts/`: seed and evaluation scripts
- `tests/`: unit tests

## Quick Start

1. Create env file:

```bash
cp .env.example .env
```

2. Start dependencies + app:

```bash
docker compose up --build
```

3. Open docs:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Local Development (without Docker)

1. Install dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run API:

```bash
uvicorn api.main:app --reload
```

3. Optional workers:

```bash
python -m workers.embedding_worker
python -m workers.sync_worker
python -m workers.campaign_worker
```

## Seed Sample Data

```bash
python scripts/seed_data.py
```

## Evaluate RAG

```bash
python scripts/evaluate_rag.py
```

## API Endpoints

### Contacts
- `POST /contacts`
- `GET /contacts?agency_id=...`
- `GET /contacts/{contact_id}`

### Campaigns
- `POST /campaigns`
- `GET /campaigns?agency_id=...`
- `POST /campaigns/{campaign_id}/activate`

### Ingestion
- `POST /ingest/properties`
- `POST /ingest/properties/from-file`

### Messaging
- `POST /sms/webhook` (Twilio inbound)
- `POST /sms/send`

### Analytics
- `GET /analytics/summary?agency_id=...`
- `GET /analytics/funnel?agency_id=...`

### Health
- `GET /health`

## Testing

```bash
pytest -q
```

## Notes

- If external services are unavailable locally, vector retrieval falls back to in-memory mode.
- If no LLM credentials are configured, deterministic fallback responses are returned.
- API key middleware uses `WEBHOOK_SECRET` via `x-api-key` header for non-webhook routes.
