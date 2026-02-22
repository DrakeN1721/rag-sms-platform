from __future__ import annotations

import pytest

from core.models import ConversationState, IntentType
from messaging.conversation import ConversationManager


@pytest.mark.asyncio
async def test_conversation_transition_valid() -> None:
    manager = ConversationManager(redis_client=None)
    convo_id = "test-convo-1"

    state = await manager.get_state(convo_id)
    assert state == ConversationState.NEW

    next_state = await manager.transition(convo_id, ConversationState.QUALIFYING)
    assert next_state == ConversationState.QUALIFYING


@pytest.mark.asyncio
async def test_conversation_transition_invalid() -> None:
    manager = ConversationManager(redis_client=None)
    convo_id = "test-convo-2"

    await manager.set_state(convo_id, ConversationState.CLOSED)
    with pytest.raises(ValueError):
        await manager.transition(convo_id, ConversationState.NURTURING)


@pytest.mark.asyncio
async def test_apply_intent_sets_closed_for_opt_out() -> None:
    manager = ConversationManager(redis_client=None)
    convo_id = "test-convo-3"

    await manager.set_state(convo_id, ConversationState.QUALIFYING)
    next_state = await manager.apply_intent(convo_id, IntentType.NOT_INTERESTED)
    assert next_state == ConversationState.CLOSED
