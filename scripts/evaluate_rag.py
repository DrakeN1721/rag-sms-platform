"""Evaluate retrieval accuracy against a small labeled benchmark."""

from __future__ import annotations

import asyncio

from core.config import get_settings
from rag.embeddings import EmbeddingClient
from rag.reranker import CrossEncoderReranker
from rag.retriever import HybridRetriever
from rag.vectorstore import QdrantVectorStore


BENCHMARK = [
    {
        "query": "Looking for waterfront home with a dock",
        "expected_listing": "MLS-1002",
    },
    {
        "query": "Need a Denver townhome with mountain view",
        "expected_listing": "MLS-1003",
    },
    {
        "query": "Want a renovated Austin bungalow near downtown",
        "expected_listing": "MLS-1001",
    },
]


async def evaluate() -> None:
    """Run benchmark and print top-k hit rate."""

    settings = get_settings()
    vectorstore = QdrantVectorStore(
        url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        api_key=settings.qdrant_api_key,
    )
    try:
        await vectorstore.ensure_collection()
    except Exception:
        vectorstore = QdrantVectorStore(url="memory://local", collection_name=settings.qdrant_collection)

    embeddings = EmbeddingClient(settings=settings)
    reranker = CrossEncoderReranker(cohere_api_key=settings.cohere_api_key)
    retriever = HybridRetriever(embeddings=embeddings, vectorstore=vectorstore, reranker=reranker)

    hits = 0
    for row in BENCHMARK:
        docs = await retriever.retrieve(
            query=row["query"],
            agency_id=settings.default_agency_id,
            top_k=3,
        )
        listing_ids = {str(doc.payload.get("listing_id")) for doc in docs}
        expected = row["expected_listing"]
        success = expected in listing_ids
        hits += 1 if success else 0
        print(f"Query: {row['query']}")
        print(f"Expected: {expected}")
        print(f"Retrieved: {sorted(listing_ids)}")
        print(f"Hit: {success}")
        print("-")

    total = len(BENCHMARK)
    accuracy = hits / total if total else 0.0
    print(f"Top-3 accuracy: {accuracy:.2%} ({hits}/{total})")

    await vectorstore.close()


if __name__ == "__main__":
    asyncio.run(evaluate())
