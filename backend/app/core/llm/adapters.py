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


class GeminiAdapter:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self._api_key = api_key
        self._model = model

    async def generate(self, messages: list[dict], **kwargs) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._api_key)

        # Gemini separates system instruction from turn-based contents.
        # Role "assistant" in OpenAI/Anthropic convention maps to "model" in Gemini.
        system_msg = ""
        contents: list = []
        for msg in messages:
            role = msg.get("role", "user")
            content_text = msg.get("content", "")
            if role == "system":
                system_msg = content_text
                continue
            gemini_role = "user" if role == "user" else "model"
            contents.append(
                types.Content(role=gemini_role, parts=[types.Part(text=content_text)])
            )

        config_kwargs: dict = {
            "temperature": kwargs.get("temperature", 0.7),
            "max_output_tokens": kwargs.get("max_tokens", 4096),
        }
        if system_msg:
            config_kwargs["system_instruction"] = system_msg

        response = await client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return response.text or ""
