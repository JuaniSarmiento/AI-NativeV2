"""Unit tests for FallbackLLMAdapter — automatic failover between adapters."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.tutor.llm_adapter import (
    ChatMessage,
    FallbackLLMAdapter,
    LLMUnavailableError,
    LLMUsage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(tokens: list[str], *, raises: Exception | None = None) -> MagicMock:
    """Build a mock LLMAdapter that either yields *tokens* or raises *raises*."""
    adapter = MagicMock()
    adapter.model_name = "mock-model"
    adapter.last_usage = LLMUsage(input_tokens=10, output_tokens=len(tokens))

    async def _stream(*args, **kwargs):
        if raises is not None:
            raise raises
        for token in tokens:
            yield token

    adapter.stream_response = _stream
    return adapter


_MESSAGES = [ChatMessage(role="user", content="Hello")]
_SYSTEM = "You are a tutor."


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_primary_succeeds_secondary_not_called():
    """When primary succeeds, secondary adapter must never be invoked."""
    primary = _make_adapter(["Hello", " world"])
    secondary = _make_adapter(["fallback"])

    adapter = FallbackLLMAdapter(primary, secondary)
    collected: list[str] = []

    async for token in adapter.stream_response(_MESSAGES, _SYSTEM):
        collected.append(token)

    assert collected == ["Hello", " world"]
    assert adapter.model_name == "mock-model"
    # secondary.stream_response should never have been awaited
    assert secondary.stream_response is not primary.stream_response


@pytest.mark.anyio
async def test_primary_unavailable_falls_back_to_secondary():
    """On LLMUnavailableError from primary, secondary tokens are yielded."""
    primary = _make_adapter([], raises=LLMUnavailableError())
    secondary = _make_adapter(["fallback", " token"])

    adapter = FallbackLLMAdapter(primary, secondary)
    collected: list[str] = []

    async for token in adapter.stream_response(_MESSAGES, _SYSTEM):
        collected.append(token)

    assert collected == ["fallback", " token"]
    # Active adapter should now point to secondary
    assert adapter._active_adapter is secondary


@pytest.mark.anyio
async def test_both_fail_raises_llm_unavailable():
    """When both primary and secondary raise LLMUnavailableError, the error propagates."""
    primary = _make_adapter([], raises=LLMUnavailableError())
    secondary = _make_adapter([], raises=LLMUnavailableError())

    adapter = FallbackLLMAdapter(primary, secondary)

    with pytest.raises(LLMUnavailableError):
        async for _ in adapter.stream_response(_MESSAGES, _SYSTEM):
            pass


@pytest.mark.anyio
async def test_last_usage_delegates_to_active_adapter():
    """last_usage returns the active adapter's usage."""
    primary = _make_adapter(["ok"])
    secondary_usage = LLMUsage(input_tokens=5, output_tokens=3)
    secondary = _make_adapter([], raises=None)
    secondary.last_usage = secondary_usage

    adapter = FallbackLLMAdapter(primary, secondary)

    # Before any call, active = primary
    assert adapter.last_usage == primary.last_usage

    # Force active to secondary
    adapter._active_adapter = secondary
    assert adapter.last_usage == secondary_usage


@pytest.mark.anyio
async def test_model_name_reflects_active_adapter():
    """model_name must reflect whichever adapter is currently active."""
    primary = _make_adapter(["token"])
    primary.model_name = "primary-model"
    secondary = _make_adapter([])
    secondary.model_name = "secondary-model"

    adapter = FallbackLLMAdapter(primary, secondary)
    assert adapter.model_name == "primary-model"

    adapter._active_adapter = secondary
    assert adapter.model_name == "secondary-model"


@pytest.mark.anyio
async def test_fallback_logs_warning(caplog):
    """A warning log must be emitted when falling back to secondary."""
    import logging

    primary = _make_adapter([], raises=LLMUnavailableError())
    secondary = _make_adapter(["ok"])

    adapter = FallbackLLMAdapter(primary, secondary)

    with caplog.at_level(logging.WARNING, logger="app.features.tutor.llm_adapter"):
        collected = []
        async for token in adapter.stream_response(_MESSAGES, _SYSTEM):
            collected.append(token)

    assert collected == ["ok"]
    assert any("falling back to secondary" in record.message for record in caplog.records)
