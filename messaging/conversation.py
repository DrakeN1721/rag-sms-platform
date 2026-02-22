"""Conversation state machine backed by Redis with in-memory fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from core.models import ConversationState, IntentType


@dataclass(slots=True)
class ConversationSnapshot:
    """Current conversation state and recent message history."""

    state: ConversationState
    history: list[dict[str, Any]]


class ConversationManager:
    """Tracks per-conversation lifecycle and short-term memory."""

    _ALLOWED_TRANSITIONS: dict[ConversationState, set[ConversationState]] = {
        ConversationState.NEW: {ConversationState.QUALIFYING, ConversationState.NURTURING, ConversationState.CLOSED},
        ConversationState.QUALIFYING: {
            ConversationState.NURTURING,
            ConversationState.HOT_LEAD,
            ConversationState.CLOSED,
        },
        ConversationState.NURTURING: {ConversationState.HOT_LEAD, ConversationState.CLOSED, ConversationState.QUALIFYING},
        ConversationState.HOT_LEAD: {ConversationState.CLOSED, ConversationState.NURTURING},
        ConversationState.CLOSED: set(),
    }

    def __init__(self, redis_client: Redis | None = None, ttl_seconds: int = 60 * 60 * 24 * 30) -> None:
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self._state_cache: dict[str, ConversationState] = {}
        self._history_cache: dict[str, list[dict[str, Any]]] = {}

    async def get_snapshot(self, conversation_id: str) -> ConversationSnapshot:
        """Return current state and recent history."""

        state = await self.get_state(conversation_id)
        history = await self.get_history(conversation_id)
        return ConversationSnapshot(state=state, history=history)

    async def get_state(self, conversation_id: str) -> ConversationState:
        """Fetch conversation state."""

        key = self._state_key(conversation_id)
        if self.redis:
            raw = await self.redis.get(key)
            if raw:
                return ConversationState(raw.decode("utf-8"))

        return self._state_cache.get(conversation_id, ConversationState.NEW)

    async def set_state(self, conversation_id: str, next_state: ConversationState) -> ConversationState:
        """Set state without transition enforcement."""

        key = self._state_key(conversation_id)
        if self.redis:
            await self.redis.set(key, next_state.value, ex=self.ttl_seconds)

        self._state_cache[conversation_id] = next_state
        return next_state

    async def transition(self, conversation_id: str, next_state: ConversationState) -> ConversationState:
        """Transition state if allowed by state machine."""

        current = await self.get_state(conversation_id)
        if next_state == current:
            return current

        if next_state not in self._ALLOWED_TRANSITIONS[current]:
            raise ValueError(f"Invalid transition from {current.value} to {next_state.value}")

        return await self.set_state(conversation_id=conversation_id, next_state=next_state)

    async def apply_intent(self, conversation_id: str, intent: IntentType) -> ConversationState:
        """Infer and apply next state from classified intent."""

        target = self._state_for_intent(intent)
        return await self.transition(conversation_id=conversation_id, next_state=target)

    async def append_message(self, conversation_id: str, direction: str, body: str) -> None:
        """Persist short message history for prompt context."""

        event = {"direction": direction, "body": body}
        list_key = self._history_key(conversation_id)

        if self.redis:
            await self.redis.rpush(list_key, json.dumps(event))
            await self.redis.ltrim(list_key, -20, -1)
            await self.redis.expire(list_key, self.ttl_seconds)

        history = self._history_cache.setdefault(conversation_id, [])
        history.append(event)
        if len(history) > 20:
            del history[:-20]

    async def get_history(self, conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent history in chronological order."""

        list_key = self._history_key(conversation_id)
        if self.redis:
            raw_items = await self.redis.lrange(list_key, -limit, -1)
            return [json.loads(item.decode("utf-8")) for item in raw_items]

        return self._history_cache.get(conversation_id, [])[-limit:]

    @staticmethod
    def _state_for_intent(intent: IntentType) -> ConversationState:
        mapping = {
            IntentType.BUYER: ConversationState.QUALIFYING,
            IntentType.SELLER: ConversationState.QUALIFYING,
            IntentType.INVESTOR: ConversationState.NURTURING,
            IntentType.RENTER: ConversationState.NURTURING,
            IntentType.NOT_INTERESTED: ConversationState.CLOSED,
            IntentType.UNKNOWN: ConversationState.NURTURING,
        }
        return mapping[intent]

    @staticmethod
    def _state_key(conversation_id: str) -> str:
        return f"conversation:{conversation_id}:state"

    @staticmethod
    def _history_key(conversation_id: str) -> str:
        return f"conversation:{conversation_id}:history"
