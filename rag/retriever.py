"""Hybrid retriever combining semantic search and BM25 keyword matching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rank_bm25 import BM25Okapi

from rag.embeddings import EmbeddingClient
from rag.reranker import CrossEncoderReranker, RerankCandidate
from rag.vectorstore import QdrantVectorStore


@dataclass(slots=True)
class RetrievedDocument:
    """Final ranked retrieval result."""

    point_id: str
    text: str
    score: float
    payload: dict[str, Any]


class HybridRetriever:
    """Retrieve relevant chunks using semantic + lexical + reranking pipeline."""

    def __init__(
        self,
        embeddings: EmbeddingClient,
        vectorstore: QdrantVectorStore,
        reranker: CrossEncoderReranker,
    ) -> None:
        self.embeddings = embeddings
        self.vectorstore = vectorstore
        self.reranker = reranker

    async def retrieve(
        self,
        query: str,
        agency_id: str,
        top_k: int = 8,
    ) -> list[RetrievedDocument]:
        """Return most relevant documents for the query and agency."""

        query_vector = await self.embeddings.embed_query(query)

        semantic_hits = await self.vectorstore.search(
            query_vector=query_vector,
            limit=max(top_k * 2, 10),
            filters={"agency_id": agency_id},
        )

        payloads = await self.vectorstore.scroll_payloads(filters={"agency_id": agency_id}, limit=300)
        keyword_scores = self._bm25_scores(query=query, payloads=payloads)

        merged: dict[str, RerankCandidate] = {}
        for hit in semantic_hits:
            text = str(hit.payload.get("text", ""))
            semantic_score = max(0.0, min(1.0, (hit.score + 1.0) / 2.0))
            merged[hit.point_id] = RerankCandidate(
                point_id=hit.point_id,
                text=text,
                score=semantic_score,
                payload=hit.payload,
                source_scores={"semantic": semantic_score},
            )

        for point_id, keyword in keyword_scores.items():
            candidate = merged.get(point_id)
            if candidate is None:
                payload = next((p for p in payloads if str(p.get("point_id")) == point_id), None)
                if payload is None:
                    continue
                candidate = RerankCandidate(
                    point_id=point_id,
                    text=str(payload.get("text", "")),
                    score=0.0,
                    payload=payload,
                    source_scores={},
                )
                merged[point_id] = candidate
            candidate.source_scores["keyword"] = keyword
            candidate.score = (candidate.source_scores.get("semantic", 0.0) * 0.65) + (keyword * 0.35)

        reranked = await self.reranker.rerank(query=query, candidates=list(merged.values()), top_n=top_k)

        return [
            RetrievedDocument(
                point_id=item.point_id,
                text=item.text,
                score=item.score,
                payload=item.payload,
            )
            for item in reranked
        ]

    @staticmethod
    def _bm25_scores(query: str, payloads: list[dict[str, Any]]) -> dict[str, float]:
        corpus = [str(payload.get("text", "")).lower().split() for payload in payloads]
        if not corpus:
            return {}

        bm25 = BM25Okapi(corpus)
        query_tokens = query.lower().split()
        raw_scores = bm25.get_scores(query_tokens)

        if len(raw_scores) == 0:
            return {}

        max_score = max(raw_scores)
        if max_score <= 0:
            return {}

        scores: dict[str, float] = {}
        for payload, raw in zip(payloads, raw_scores, strict=False):
            point_id = str(payload.get("point_id", ""))
            if not point_id or raw <= 0:
                continue
            scores[point_id] = float(raw / max_score)

        return scores
