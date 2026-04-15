from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMAdapter(Protocol):
    async def generate(self, messages: list[dict], **kwargs) -> str: ...


class OpenAIAdapter:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key
        self._model = model

    async def generate(self, messages: list[dict], **kwargs) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key)
        response = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        return response.choices[0].message.content or ""


class AnthropicAdapter:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        self._api_key = api_key
        self._model = model

    async def generate(self, messages: list[dict], **kwargs) -> str:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self._api_key)

        # Anthropic separates system from user messages
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)

        response = await client.messages.create(
            model=self._model,
            max_tokens=kwargs.get("max_tokens", 4096),
            system=system_msg if system_msg else anthropic.NOT_GIVEN,
            messages=user_messages,
        )
        return response.content[0].text


class MistralAdapter:
    def __init__(self, api_key: str, model: str = "mistral-small-latest") -> None:
        self._api_key = api_key
        self._model = model

    async def generate(self, messages: list[dict], **kwargs) -> str:
        from mistralai.client import Mistral

        client = Mistral(api_key=self._api_key, timeout_ms=120_000)
        response = await client.chat.complete_async(
            model=self._model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        return response.choices[0].message.content or ""
