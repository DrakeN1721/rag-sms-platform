"""FastAPI app entrypoint with service wiring and lifecycle management."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI

from api.middleware import APIKeyMiddleware, RateLimitMiddleware, RequestLoggingMiddleware
from api.routes import analytics, campaigns, contacts, ingest, sms
from campaign.scheduler import CampaignScheduler
from core.config import get_settings
from core.database import healthcheck, init_db
from crm.gohighlevel import GoHighLevelClient
from crm.sync import CRMSyncService
from intelligence.intent import IntentClassifier
from intelligence.next_action import NextBestActionRecommender
from intelligence.propensity import PropensityModel
from llm.client import LLMClient
from llm.evaluator import ResponseEvaluator
from messaging.conversation import ConversationManager
from messaging.router import IntentRouter
from messaging.twilio_handler import TwilioService
from rag.embeddings import EmbeddingClient
from rag.ingestor import PropertyIngestor
from rag.reranker import CrossEncoderReranker
from rag.retriever import HybridRetriever
from rag.vectorstore import QdrantVectorStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and tear down external dependencies."""

    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    await init_db()

    redis_client = None
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
    except Exception:  # pragma: no cover - startup fallback
        redis_client = None

    vectorstore = QdrantVectorStore(
        url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        vector_size=1536,
        api_key=settings.qdrant_api_key,
    )
    try:
        await vectorstore.ensure_collection()
    except Exception:  # pragma: no cover - startup fallback
        vectorstore = QdrantVectorStore(
            url="memory://local",
            collection_name=settings.qdrant_collection,
            vector_size=1536,
        )

    embeddings = EmbeddingClient(settings=settings)
    reranker = CrossEncoderReranker(cohere_api_key=settings.cohere_api_key)
    retriever = HybridRetriever(embeddings=embeddings, vectorstore=vectorstore, reranker=reranker)
    ingestor_service = PropertyIngestor(embeddings=embeddings, vectorstore=vectorstore, settings=settings)

    app.state.settings = settings
    app.state.redis = redis_client
    app.state.vectorstore = vectorstore
    app.state.embeddings = embeddings
    app.state.reranker = reranker
    app.state.retriever = retriever
    app.state.ingestor = ingestor_service

    app.state.llm_client = LLMClient(settings=settings)
    app.state.evaluator = ResponseEvaluator()
    app.state.twilio = TwilioService(settings=settings)

    app.state.intent_classifier = IntentClassifier()
    app.state.propensity_model = PropensityModel()
    app.state.intent_router = IntentRouter()
    app.state.next_action = NextBestActionRecommender()
    app.state.conversation_manager = ConversationManager(redis_client=redis_client)

    crm_client = GoHighLevelClient(
        api_key=settings.gohighlevel_api_key,
        location_id=settings.gohighlevel_location_id,
    )
    app.state.crm_client = crm_client
    app.state.crm_sync = CRMSyncService(client=crm_client)

    campaign_scheduler = CampaignScheduler()
    campaign_scheduler.start()
    app.state.campaign_scheduler = campaign_scheduler

    try:
        yield
    finally:
        campaign_scheduler.shutdown()
        if redis_client:
            await redis_client.close()
        await vectorstore.close()


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=240, excluded_paths={"/health"})
app.add_middleware(
    APIKeyMiddleware,
    api_key=settings.webhook_secret,
    excluded_paths={"/health", "/sms/webhook"},
)

app.include_router(contacts.router)
app.include_router(campaigns.router)
app.include_router(ingest.router)
app.include_router(analytics.router)
app.include_router(sms.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Basic health endpoint for container probes."""

    await healthcheck()
    return {"status": "ok"}
