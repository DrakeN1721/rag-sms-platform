from __future__ import annotations

import pytest

from rag.chunker import chunk_text
from rag.reranker import CrossEncoderReranker
from rag.retriever import HybridRetriever
from rag.vectorstore import QdrantVectorStore, VectorPoint


class FakeEmbeddingClient:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @staticmethod
    def _embed(text: str) -> list[float]:
        text = text.lower()
        if "waterfront" in text:
            return [0.9, 0.1, 0.0]
        if "mountain" in text:
            return [0.1, 0.9, 0.0]
        return [0.0, 0.1, 0.9]


def test_chunk_text_overlap() -> None:
    text = "a" * 1000
    chunks = chunk_text(text, chunk_size=300, chunk_overlap=50)
    assert len(chunks) == 4
    assert len(chunks[0]) == 300
    assert len(chunks[1]) == 300


@pytest.mark.asyncio
async def test_hybrid_retriever_prefers_semantic_match() -> None:
    embeddings = FakeEmbeddingClient()
    vectorstore = QdrantVectorStore(url="memory://test", collection_name="properties", vector_size=3)
    reranker = CrossEncoderReranker(cohere_api_key=None)

    await vectorstore.upsert(
        [
            VectorPoint(
                point_id="p1",
                vector=[0.9, 0.1, 0.0],
                payload={
                    "point_id": "p1",
                    "agency_id": "agency-demo",
                    "listing_id": "MLS-1002",
                    "text": "Waterfront home with private dock and pool",
                },
            ),
            VectorPoint(
                point_id="p2",
                vector=[0.1, 0.9, 0.0],
                payload={
                    "point_id": "p2",
                    "agency_id": "agency-demo",
                    "listing_id": "MLS-1003",
                    "text": "Mountain view townhome near trails",
                },
            ),
        ]
    )

    retriever = HybridRetriever(embeddings=embeddings, vectorstore=vectorstore, reranker=reranker)
    docs = await retriever.retrieve("show me waterfront properties", agency_id="agency-demo", top_k=2)

    assert docs
    assert docs[0].payload["listing_id"] == "MLS-1002"
