"""Unit tests for AnthropicAdapter — mocked SDK."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.tutor.llm_adapter import (
    AnthropicAdapter,
    ChatMessage,
    LLMError,
    LLMRateLimitError,
    LLMUnavailableError,
)


@pytest.fixture
def mock_settings():
    with patch("app.features.tutor.llm_adapter.get_settings") as mock:
        settings = MagicMock()
        settings.anthropic_api_key = "test-key"
        settings.anthropic_model = "claude-test"
        settings.anthropic_max_tokens = 512
        settings.anthropic_timeout_seconds = 10
        mock.return_value = settings
        yield settings


def test_adapter_model_name(mock_settings):
    adapter = AnthropicAdapter()
    assert adapter.model_name == "claude-test"


def test_adapter_initial_usage_is_none(mock_settings):
    adapter = AnthropicAdapter()
    assert adapter.last_usage is None


async def test_adapter_raises_on_rate_limit(mock_settings):
    import anthropic

    adapter = AnthropicAdapter()

    with patch.object(adapter._client.messages, "stream") as mock_stream:
        mock_stream.side_effect = anthropic.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429),
            body={},
        )

        with pytest.raises(LLMRateLimitError):
            async for _ in adapter.stream_response(
                [ChatMessage(role="user", content="test")],
                "system prompt",
            ):
                pass


async def test_adapter_raises_on_timeout(mock_settings):
    import anthropic

    adapter = AnthropicAdapter()

    with patch.object(adapter._client.messages, "stream") as mock_stream:
        mock_stream.side_effect = anthropic.APITimeoutError(request=MagicMock())

        with pytest.raises(LLMUnavailableError):
            async for _ in adapter.stream_response(
                [ChatMessage(role="user", content="test")],
                "system prompt",
            ):
                pass
