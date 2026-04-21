from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import AsyncIterator

from app.config import get_settings
from app.core.exceptions import DomainError
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain exceptions for LLM layer
# ---------------------------------------------------------------------------


class LLMError(DomainError):
    default_message = "LLM request failed."
    default_code = "LLM_ERROR"


class LLMRateLimitError(LLMError):
    default_message = "LLM provider rate limit exceeded."
    default_code = "LLM_RATE_LIMITED"


class LLMUnavailableError(LLMError):
    default_message = "LLM provider is unavailable."
    default_code = "LLM_UNAVAILABLE"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class StreamResult:
    """Holds the full response text and usage after streaming completes."""
    text: str
    usage: LLMUsage


# ---------------------------------------------------------------------------
# Abstract adapter
# ---------------------------------------------------------------------------


class LLMAdapter(abc.ABC):
    @abc.abstractmethod
    async def stream_response(
        self,
        messages: list[ChatMessage],
        system_prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield string tokens as they arrive from the LLM.

        After the iterator is exhausted, ``last_usage`` contains token counts.
        """
        ...  # pragma: no cover

    @property
    @abc.abstractmethod
    def last_usage(self) -> LLMUsage | None:
        """Token usage from the most recent completed stream."""
        ...  # pragma: no cover

    async def complete(
        self,
        messages: list[ChatMessage],
        system_prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> StreamResult:
        """Non-streaming completion. Default: collect stream tokens."""
        parts: list[str] = []
        async for token in self.stream_response(messages, system_prompt, max_tokens=max_tokens):
            parts.append(token)
        text = "".join(parts)
        usage = self.last_usage or LLMUsage(input_tokens=0, output_tokens=0)
        return StreamResult(text=text, usage=usage)

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# Anthropic implementation
# ---------------------------------------------------------------------------


class AnthropicAdapter(LLMAdapter):
    def __init__(self) -> None:
        settings = get_settings()

        try:
            import anthropic  # type: ignore
        except ModuleNotFoundError as exc:
            raise LLMUnavailableError(
                message="Anthropic SDK is not installed. Install 'anthropic' or use TUTOR_LLM_PROVIDER=mistral.",
            ) from exc

        self._anthropic = anthropic
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.anthropic_timeout_seconds,
        )
        self._model = settings.anthropic_model
        self._default_max_tokens = settings.anthropic_max_tokens
        self._last_usage: LLMUsage | None = None

    @property
    def last_usage(self) -> LLMUsage | None:
        return self._last_usage

    @property
    def model_name(self) -> str:
        return self._model

    async def stream_response(
        self,
        messages: list[ChatMessage],
        system_prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        api_messages = [{"role": m.role, "content": m.content} for m in messages]
        tokens = max_tokens or self._default_max_tokens

        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=tokens,
                system=system_prompt,
                messages=api_messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

                # After stream ends, capture usage
                response = await stream.get_final_message()
                self._last_usage = LLMUsage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )

        except self._anthropic.RateLimitError as exc:
            logger.warning("Anthropic rate limit hit", extra={"error": str(exc)})
            raise LLMRateLimitError() from exc
        except (self._anthropic.APIConnectionError, self._anthropic.APITimeoutError) as exc:
            logger.error("Anthropic unavailable", extra={"error": str(exc)})
            raise LLMUnavailableError() from exc
        except self._anthropic.APIError as exc:
            logger.error("Anthropic API error", extra={"status": exc.status_code, "error": str(exc)})
            raise LLMError(message=f"LLM error: {exc.message}") from exc


# ---------------------------------------------------------------------------
# Mistral implementation
# ---------------------------------------------------------------------------


class MistralAdapter(LLMAdapter):
    def __init__(self) -> None:
        settings = get_settings()
        from mistralai.client import Mistral

        self._client = Mistral(api_key=settings.mistral_api_key)
        self._model = settings.mistral_model
        self._default_max_tokens = settings.mistral_max_tokens
        self._last_usage: LLMUsage | None = None

    @property
    def last_usage(self) -> LLMUsage | None:
        return self._last_usage

    @property
    def model_name(self) -> str:
        return self._model

    async def stream_response(
        self,
        messages: list[ChatMessage],
        system_prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        api_messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            *[{"role": m.role, "content": m.content} for m in messages],
        ]
        tokens = max_tokens or self._default_max_tokens

        try:
            stream = await self._client.chat.stream_async(
                model=self._model,
                max_tokens=tokens,
                messages=api_messages,  # type: ignore[arg-type]
            )

            input_tokens = 0
            output_tokens = 0

            async for event in stream:
                data = event.data
                if data.choices:
                    choice = data.choices[0]
                    delta = choice.delta
                    if delta and delta.content:
                        yield delta.content

                if data.usage:
                    input_tokens = data.usage.prompt_tokens or 0
                    output_tokens = data.usage.completion_tokens or 0

            self._last_usage = LLMUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        except Exception as exc:
            error_str = str(exc).lower()
            if "rate" in error_str and "limit" in error_str:
                logger.warning("Mistral rate limit hit", extra={"error": str(exc)})
                raise LLMRateLimitError() from exc
            if "timeout" in error_str or "connect" in error_str:
                logger.error("Mistral unavailable", extra={"error": str(exc)})
                raise LLMUnavailableError() from exc
            logger.error("Mistral API error", extra={"error": str(exc)})
            raise LLMError(message=f"LLM error: {exc}") from exc


# ---------------------------------------------------------------------------
# Fallback adapter — wraps primary + secondary with automatic failover
# ---------------------------------------------------------------------------


class FallbackLLMAdapter(LLMAdapter):
    """Wraps primary + secondary adapters with automatic failover.

    On ``LLMUnavailableError`` from the primary adapter, transparently
    switches to the secondary and continues yielding tokens.

    TODO: The caller (router/service) should detect that ``model_name``
    changed between the start and end of a stream and log a governance event
    for the provider switch.  The adapter itself has no DB access and cannot
    write governance events directly.
    """

    def __init__(self, primary: LLMAdapter, secondary: LLMAdapter) -> None:
        self._primary = primary
        self._secondary = secondary
        self._active_adapter: LLMAdapter = primary

    @property
    def last_usage(self) -> LLMUsage | None:
        return self._active_adapter.last_usage

    @property
    def model_name(self) -> str:
        return self._active_adapter.model_name

    async def stream_response(
        self,
        messages: list[ChatMessage],
        system_prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        try:
            self._active_adapter = self._primary
            async for token in self._primary.stream_response(
                messages, system_prompt, max_tokens=max_tokens
            ):
                yield token
        except LLMUnavailableError:
            logger.warning(
                "LLM primary provider unavailable — falling back to secondary",
                extra={
                    "primary": self._primary.model_name,
                    "secondary": self._secondary.model_name,
                },
            )
            self._active_adapter = self._secondary
            async for token in self._secondary.stream_response(
                messages, system_prompt, max_tokens=max_tokens
            ):
                yield token
