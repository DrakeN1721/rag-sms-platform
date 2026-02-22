"""Candidate reranking implementations for retrieval outputs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RerankCandidate:
    """A candidate chunk/document for reranking."""

    point_id: str
    text: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)
    source_scores: dict[str, float] = field(default_factory=dict)


class CrossEncoderReranker:
    """Cohere-based reranker with lexical fallback."""

    def __init__(self, cohere_api_key: str | None = None) -> None:
        self.cohere_api_key = cohere_api_key

    async def rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankCandidate]:
        """Return candidates ordered by relevance."""

        if not candidates:
            return []

        if self.cohere_api_key:
            try:
                ranked = await self._cohere_rerank(query=query, candidates=candidates, top_n=top_n)
                if ranked:
                    return ranked
            except Exception as exc:  # pragma: no cover - network runtime fallback
                logger.warning("Cohere rerank failed: %s", exc)

        return self._lexical_rerank(query=query, candidates=candidates, top_n=top_n)

    async def _cohere_rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankCandidate]:
        docs = [candidate.text for candidate in candidates]
        payload = {
            "model": "rerank-v3.5",
            "query": query,
            "documents": docs,
            "top_n": min(top_n, len(docs)),
        }
        headers = {
            "Authorization": f"Bearer {self.cohere_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post("https://api.cohere.com/v2/rerank", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        output: list[RerankCandidate] = []
        for item in data.get("results", []):
            index = int(item["index"])
            relevance = float(item["relevance_score"])
            candidate = candidates[index]
            output.append(
                RerankCandidate(
                    point_id=candidate.point_id,
                    text=candidate.text,
                    score=relevance,
                    payload=candidate.payload,
                    source_scores={**candidate.source_scores, "rerank": relevance},
                )
            )

        return output

    @staticmethod
    def _lexical_rerank(
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankCandidate]:
        query_tokens = set(query.lower().split())

        rescored: list[RerankCandidate] = []
        for candidate in candidates:
            doc_tokens = set(candidate.text.lower().split())
            overlap = len(query_tokens & doc_tokens)
            lexical = overlap / max(1, len(query_tokens))
            score = (candidate.score * 0.6) + (lexical * 0.4)
            rescored.append(
                RerankCandidate(
                    point_id=candidate.point_id,
                    text=candidate.text,
                    score=score,
                    payload=candidate.payload,
                    source_scores={**candidate.source_scores, "lexical": lexical},
                )
            )

        rescored.sort(key=lambda item: item.score, reverse=True)
        return rescored[:top_n]
