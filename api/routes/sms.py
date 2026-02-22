"""Twilio SMS webhook and send endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.database import ContactORM, ConversationORM, MessageORM, get_db_session
from core.models import ConversationState
from intelligence.propensity import EngagementSignals
from llm.prompts import LEAD_NURTURING_TEMPLATE, render_prompt

router = APIRouter(prefix="/sms", tags=["sms"])


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SendSMSRequest(BaseModel):
    to_phone: str
    body: str
    from_phone: str | None = None


@router.post("/send")
async def send_sms(payload: SendSMSRequest, request: Request) -> dict[str, str]:
    """Send an outbound SMS through Twilio."""

    sid = await request.app.state.twilio.send_sms(
        to_phone=payload.to_phone,
        body=payload.body,
        from_phone=payload.from_phone,
    )
    return {"message_sid": sid}


@router.post("/webhook")
async def twilio_webhook(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    """Handle inbound Twilio SMS and return TwiML reply."""

    settings = get_settings()
    twilio = request.app.state.twilio

    form = await request.form()
    form_data = {str(key): str(value) for key, value in form.items()}

    signature = request.headers.get("X-Twilio-Signature")
    if not twilio.validate_signature(str(request.url), form_data, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    inbound = twilio.parse_inbound(form_data)
    if not inbound.body:
        return Response(content=twilio.twiml_response("Please send a message so I can help."), media_type="application/xml")

    agency_id = settings.default_agency_id

    contact = await _get_or_create_contact(db=db, agency_id=agency_id, phone=inbound.from_phone)
    conversation = await _get_or_create_conversation(db=db, agency_id=agency_id, contact_id=str(contact.id))

    conversation_manager = request.app.state.conversation_manager
    await conversation_manager.append_message(str(conversation.id), direction="inbound", body=inbound.body)

    classifier = request.app.state.intent_classifier
    prediction = await classifier.classify(inbound.body)

    total_messages = (
        await db.execute(select(func.count()).select_from(MessageORM).where(MessageORM.conversation_id == conversation.id))
    ).scalar_one()
    signals = EngagementSignals(
        messages_received=int(total_messages),
        replies_sent=max(1, int(total_messages // 2)),
        average_response_minutes=30.0,
        listing_clicks=0,
        tours_requested=0,
    )

    propensity_model = request.app.state.propensity_model
    propensity = propensity_model.score(signals)

    router_engine = request.app.state.intent_router
    current_state = await conversation_manager.get_state(str(conversation.id))
    decision = router_engine.route(prediction.intent, current_state, propensity)

    try:
        await conversation_manager.transition(str(conversation.id), decision.next_state)
    except ValueError:
        await conversation_manager.set_state(str(conversation.id), decision.next_state)

    conversation.state = decision.next_state.value
    conversation.last_message_at = utcnow()
    conversation.updated_at = utcnow()

    inbound_row = MessageORM(
        agency_id=agency_id,
        conversation_id=conversation.id,
        direction="inbound",
        body=inbound.body,
        intent=prediction.intent.value,
        sentiment=prediction.sentiment.value,
    )
    db.add(inbound_row)

    retriever = request.app.state.retriever
    docs = await retriever.retrieve(query=inbound.body, agency_id=agency_id, top_k=4)
    context = "\n".join(
        [
            f"- {doc.payload.get('address')} (${doc.payload.get('price')}): {doc.text[:180]}"
            for doc in docs
            if doc.text
        ]
    )

    history = await conversation_manager.get_history(str(conversation.id), limit=8)
    history_str = "\n".join(f"{item['direction']}: {item['body']}" for item in history)
    contact_profile = f"{contact.first_name} {contact.last_name} ({contact.phone})"

    system_prompt, user_prompt = render_prompt(
        LEAD_NURTURING_TEMPLATE,
        contact_profile=contact_profile,
        conversation_history=history_str or "No history",
        retrieved_context=context or "No matching properties found.",
        latest_message=inbound.body,
    )

    if prediction.intent.value == "not_interested":
        reply = "Understood. I have removed you from follow-ups. Reply START anytime to re-subscribe."
    else:
        llm_client = request.app.state.llm_client
        reply = await llm_client.complete(system_prompt=system_prompt, user_prompt=user_prompt)

    if len(reply) > 640:
        reply = reply[:637] + "..."

    outbound_row = MessageORM(
        agency_id=agency_id,
        conversation_id=conversation.id,
        direction="outbound",
        body=reply,
        intent="unknown",
        sentiment="neutral",
    )
    db.add(outbound_row)

    await conversation_manager.append_message(str(conversation.id), direction="outbound", body=reply)

    conversation.updated_at = utcnow()
    await db.commit()

    return Response(content=twilio.twiml_response(reply), media_type="application/xml")


async def _get_or_create_contact(db: AsyncSession, agency_id: str, phone: str) -> ContactORM:
    row = (
        await db.execute(select(ContactORM).where(ContactORM.agency_id == agency_id, ContactORM.phone == phone))
    ).scalar_one_or_none()
    if row:
        return row

    row = ContactORM(
        agency_id=agency_id,
        first_name="Lead",
        last_name="",
        phone=phone,
        email=None,
        tags=["inbound_sms"],
        metadata_={},
    )
    db.add(row)
    await db.flush()
    return row


async def _get_or_create_conversation(db: AsyncSession, agency_id: str, contact_id: str) -> ConversationORM:
    row = (
        await db.execute(
            select(ConversationORM).where(
                ConversationORM.agency_id == agency_id,
                ConversationORM.contact_id == contact_id,
                ConversationORM.state != ConversationState.CLOSED.value,
            )
        )
    ).scalar_one_or_none()
    if row:
        return row

    row = ConversationORM(
        agency_id=agency_id,
        contact_id=contact_id,
        state=ConversationState.NEW.value,
        summary=None,
        last_message_at=utcnow(),
    )
    db.add(row)
    await db.flush()
    return row
