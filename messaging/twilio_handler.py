"""Twilio webhook parsing, validation, and SMS sending."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Mapping

from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from core.config import Settings, get_settings


@dataclass(slots=True)
class InboundSMS:
    """Standardized inbound SMS payload."""

    from_phone: str
    to_phone: str
    body: str
    message_sid: str


class TwilioService:
    """Thin adapter over Twilio SDK with async-friendly methods."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: Client | None = None
        self._validator: RequestValidator | None = None

        if self.settings.twilio_account_sid and self.settings.twilio_auth_token:
            self._client = Client(self.settings.twilio_account_sid, self.settings.twilio_auth_token)
            self._validator = RequestValidator(self.settings.twilio_auth_token)

    def parse_inbound(self, form_data: Mapping[str, str]) -> InboundSMS:
        """Parse form-encoded Twilio webhook fields."""

        return InboundSMS(
            from_phone=form_data.get("From", ""),
            to_phone=form_data.get("To", ""),
            body=form_data.get("Body", "").strip(),
            message_sid=form_data.get("MessageSid", ""),
        )

    def validate_signature(self, url: str, form_data: Mapping[str, str], signature: str | None) -> bool:
        """Validate Twilio request signature when credentials are configured."""

        if not self._validator:
            return True
        if not signature:
            return False
        return self._validator.validate(url, dict(form_data), signature)

    async def send_sms(self, to_phone: str, body: str, from_phone: str | None = None) -> str:
        """Send SMS asynchronously via thread offload."""

        if not self._client:
            return "mock-message-sid"

        sender = from_phone or self.settings.twilio_phone_number
        if not sender:
            raise ValueError("No sender phone configured")

        message = await asyncio.to_thread(
            self._client.messages.create,
            to=to_phone,
            from_=sender,
            body=body,
        )
        return str(message.sid)

    @staticmethod
    def twiml_response(message: str) -> str:
        """Generate TwiML XML response body."""

        twiml = MessagingResponse()
        twiml.message(message)
        return str(twiml)
