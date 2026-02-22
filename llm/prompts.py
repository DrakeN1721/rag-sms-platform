"""Prompt templates used across lead nurturing workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Simple string template wrapper."""

    system: str
    user: str


LEAD_NURTURING_TEMPLATE = PromptTemplate(
    system=(
        "You are an expert real-estate lead nurturing assistant. "
        "Keep messages concise, helpful, and compliant with SMS etiquette. "
        "Never invent listing facts."
    ),
    user=(
        "Contact profile:\n{contact_profile}\n\n"
        "Conversation history:\n{conversation_history}\n\n"
        "Relevant listings:\n{retrieved_context}\n\n"
        "Latest inbound message: {latest_message}\n"
        "Write a short, natural SMS response and include one clear next step."
    ),
)

PROPERTY_MATCH_TEMPLATE = PromptTemplate(
    system=(
        "You match buyer intent to real estate listings using only supplied context. "
        "Return practical reasoning and avoid unsupported claims."
    ),
    user=(
        "Buyer criteria: {criteria}\n"
        "Candidate properties:\n{retrieved_context}\n\n"
        "Recommend top matches with concise reasons."
    ),
)

INTENT_CLASSIFICATION_TEMPLATE = PromptTemplate(
    system=(
        "Classify SMS lead intent and sentiment. "
        "Return strict JSON with fields: intent, sentiment, next_action, confidence."
    ),
    user="Message: {message}",
)


def render_prompt(template: PromptTemplate, **kwargs: str) -> tuple[str, str]:
    """Render template into system and user strings."""

    return template.system.format(**kwargs), template.user.format(**kwargs)
