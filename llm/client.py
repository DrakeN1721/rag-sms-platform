"""Unified async client for OpenAI and Anthropic chat APIs."""

from __future__ import annotations

from typing import Literal

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from core.config import Settings, get_settings

Provider = Literal["openai", "anthropic"]


class LLMClient:
    """Provider-agnostic text generation client."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.provider: Provider = self.settings.llm_provider.lower()  # type: ignore[assignment]
        self._openai: AsyncOpenAI | None = None
        self._anthropic: AsyncAnthropic | None = None

        if self.settings.openai_api_key:
            self._openai = AsyncOpenAI(api_key=self.settings.openai_api_key)
        if self.settings.anthropic_api_key:
            self._anthropic = AsyncAnthropic(api_key=self.settings.anthropic_api_key)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 350,
    ) -> str:
        """Generate a completion from the configured LLM provider."""

        if self.provider == "openai" and self._openai:
            response = await self._openai.chat.completions.create(
                model=self.settings.llm_model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content
            return content or ""

        if self.provider == "anthropic" and self._anthropic:
            response = await self._anthropic.messages.create(
                model=self.settings.llm_model,
                temperature=temperature,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            parts = [chunk.text for chunk in response.content if getattr(chunk, "type", "") == "text"]
            return "\n".join(parts)

        return self._fallback(system_prompt=system_prompt, user_prompt=user_prompt)

    @staticmethod
    def _fallback(system_prompt: str, user_prompt: str) -> str:
        """Safe deterministic fallback when provider credentials are unavailable."""

        snippet = user_prompt[-280:].strip().replace("\n", " ")
        return (
            "Thanks for the message. Based on what you shared, "
            "I can send options that match your criteria and budget. "
            f"Quick context: {snippet[:120]}"
        )
