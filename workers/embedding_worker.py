"""Redis queue worker for asynchronous embedding ingestion jobs."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import redis.asyncio as redis

from core.config import get_settings
from rag.embeddings import EmbeddingClient
from rag.ingestor import PropertyIngestor
from rag.vectorstore import QdrantVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_job(job: dict[str, Any], ingestor: PropertyIngestor) -> None:
    """Process a single ingestion job payload."""

    agency_id = str(job.get("agency_id"))
    if not agency_id:
        raise ValueError("agency_id missing from embedding job")

    if "records" in job and isinstance(job["records"], list):
        await ingestor.ingest_records(records=job["records"], agency_id=agency_id)
        return

    file_path = job.get("file_path")
    file_type = job.get("file_type")
    if file_path and file_type == "csv":
        await ingestor.ingest_csv(file_path, agency_id=agency_id)
        return
    if file_path and file_type == "json":
        await ingestor.ingest_json(file_path, agency_id=agency_id)
        return

    raise ValueError("Unsupported embedding job payload")


async def run_worker() -> None:
    """Start worker loop until interrupted."""

    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)

    vectorstore = QdrantVectorStore(
        url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        api_key=settings.qdrant_api_key,
    )
    try:
        await vectorstore.ensure_collection()
    except Exception:  # pragma: no cover - runtime fallback
        vectorstore = QdrantVectorStore(url="memory://local", collection_name=settings.qdrant_collection)

    embeddings = EmbeddingClient(settings=settings)
    ingestor = PropertyIngestor(embeddings=embeddings, vectorstore=vectorstore, settings=settings)

    logger.info("Embedding worker started")
    try:
        while True:
            item = await redis_client.blpop("embedding_jobs", timeout=5)
            if not item:
                await asyncio.sleep(0.1)
                continue

            _, raw_job = item
            try:
                job = json.loads(raw_job)
                await process_job(job=job, ingestor=ingestor)
                logger.info("Processed embedding job")
            except Exception as exc:
                logger.exception("Failed embedding job: %s", exc)
    finally:
        await vectorstore.close()
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(run_worker())
