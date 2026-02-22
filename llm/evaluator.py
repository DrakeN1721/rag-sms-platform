"""Lightweight response quality evaluation for RAG outputs."""

from __future__ import annotations

from dataclasses import dataclass

from rag.retriever import RetrievedDocument


@dataclass(slots=True)
class EvaluationResult:
    """Evaluation summary for a generated response."""

    relevance: float
    groundedness: float
    overall: float
    notes: list[str]


class ResponseEvaluator:
    """Heuristic response evaluator suitable for online monitoring."""

    async def evaluate(
        self,
        query: str,
        response: str,
        retrieved_docs: list[RetrievedDocument],
    ) -> EvaluationResult:
        """Compute relevance and groundedness scores in [0, 1]."""

        query_tokens = set(query.lower().split())
        response_tokens = set(response.lower().split())

        overlap = len(query_tokens & response_tokens)
        relevance = overlap / max(1, len(query_tokens))

        context_tokens = set()
        for doc in retrieved_docs:
            context_tokens.update(doc.text.lower().split())

        unsupported_tokens = [
            token for token in response_tokens if token.isalpha() and len(token) > 5 and token not in context_tokens
        ]
        hallucination_penalty = min(0.6, len(unsupported_tokens) * 0.02)
        groundedness = max(0.0, 1.0 - hallucination_penalty)

        overall = (relevance * 0.6) + (groundedness * 0.4)

        notes: list[str] = []
        if relevance < 0.3:
            notes.append("Low relevance to user intent")
        if groundedness < 0.5:
            notes.append("Potential unsupported claims")

        return EvaluationResult(
            relevance=round(relevance, 3),
            groundedness=round(groundedness, 3),
            overall=round(overall, 3),
            notes=notes,
        )
