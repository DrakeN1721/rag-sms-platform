# RAG SMS Lead Nurturing Platform - MVP

## Overview
Production-ready RAG-powered SMS lead nurturing system for real estate agencies.
Manages contacts, ingests property data, runs conversational AI over SMS.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  Twilio SMS  │───▶│  FastAPI App  │───▶│   Qdrant    │
│  Webhooks    │◀───│  (async)     │◀───│  Vector DB  │
└─────────────┘    └──────┬───────┘    └─────────────┘
                          │
                   ┌──────┴───────┐
                   │              │
              ┌────▼────┐  ┌─────▼──────┐
              │  Redis   │  │  LLM API   │
              │  Queue   │  │  (Claude/  │
              │  + State │  │   OpenAI)  │
              └─────────┘  └────────────┘
```

## Module Breakdown

### 1. core/ - Shared config and models
- `config.py` - Settings via pydantic-settings (.env)
- `models.py` - Pydantic models for Contact, Conversation, Message, Property, Campaign
- `database.py` - Async SQLAlchemy (PostgreSQL) for relational data

### 2. rag/ - RAG Pipeline
- `embeddings.py` - Async embedding generation (OpenAI text-embedding-3-small)
- `vectorstore.py` - Qdrant client wrapper (create collection, upsert, search)
- `chunker.py` - Document chunking with overlap (property listings, agency knowledge base)
- `retriever.py` - Hybrid retrieval: semantic search + BM25 keyword + reranker
- `reranker.py` - Cross-encoder reranking (Cohere rerank or sentence-transformers)
- `ingestor.py` - Multi-source ingestion: CSV, JSON, API webhooks for property data

### 3. llm/ - LLM Orchestration
- `client.py` - Unified LLM client (supports OpenAI GPT-4 and Anthropic Claude)
- `prompts.py` - Prompt templates for lead nurturing, property matching, intent classification
- `structured.py` - Structured output parsing (intent, sentiment, next action)
- `evaluator.py` - Response quality evaluation (relevance scoring, hallucination detection)

### 4. messaging/ - SMS Integration
- `twilio_handler.py` - Twilio webhook receiver and SMS sender
- `conversation.py` - Conversation state machine (new, qualifying, nurturing, hot_lead, closed)
- `router.py` - Intent-based message routing

### 5. crm/ - CRM Integration
- `gohighlevel.py` - GoHighLevel API client (contacts, opportunities, tags)
- `sync.py` - Bidirectional CRM sync

### 6. campaign/ - Campaign Engine
- `scheduler.py` - Campaign scheduling with APScheduler
- `triggers.py` - Event-based triggers (new listing, price drop, contact milestone)
- `ab_test.py` - A/B test framework for message variants

### 7. intelligence/ - ML Features
- `intent.py` - Intent classifier (buyer, seller, investor, renter, not_interested)
- `propensity.py` - Lead scoring model (engagement signals, response patterns)
- `next_action.py` - Next-best-action recommender

### 8. api/ - FastAPI Application
- `main.py` - App entrypoint with lifespan events
- `routes/sms.py` - Twilio webhook endpoints
- `routes/contacts.py` - Contact CRUD + search
- `routes/campaigns.py` - Campaign management
- `routes/ingest.py` - Data ingestion endpoints
- `routes/analytics.py` - Metrics and dashboards
- `middleware.py` - Rate limiting, auth, logging

### 9. workers/ - Background Tasks
- `embedding_worker.py` - Redis queue consumer for async embedding generation
- `sync_worker.py` - CRM sync worker
- `campaign_worker.py` - Campaign execution worker

## Tech Stack
- Python 3.12 + FastAPI (async)
- Qdrant (vector database)
- PostgreSQL (relational data)
- Redis (message queue, conversation state, caching)
- OpenAI / Anthropic (LLM + embeddings)
- Twilio (SMS)
- Docker + docker-compose
- Pytest + coverage

## Key Design Decisions
- Qdrant over pgvector for production-scale vector search (HNSW, filtering, payload indexing)
- Hybrid retrieval (semantic + BM25) with cross-encoder reranking for 95%+ accuracy
- Redis for conversation state (sub-second reads, TTL for session management)
- Async everything (httpx, SQLAlchemy async, qdrant-client async)
- Multi-tenant: agency_id partition on all data
- Structured LLM outputs for deterministic routing

## Files to Create
- All modules above
- `docker-compose.yml` (app, qdrant, postgres, redis)
- `Dockerfile`
- `.env.example`
- `requirements.txt`
- `README.md` with architecture diagram, setup guide, API docs
- `tests/` with unit tests for RAG pipeline, intent classifier, conversation state
- `scripts/seed_data.py` - Seed sample property data + contacts
- `scripts/evaluate_rag.py` - RAG accuracy evaluation script
