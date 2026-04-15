from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm.adapters import AnthropicAdapter, OpenAIAdapter


@pytest.mark.asyncio
async def test_openai_adapter_calls_chat_completions():
    adapter = OpenAIAdapter(api_key="test-key", model="gpt-4o-mini")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"title": "Test"}'))]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        result = await adapter.generate([
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Generate something"},
        ])

    assert result == '{"title": "Test"}'
    mock_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_anthropic_adapter_calls_messages_api():
    adapter = AnthropicAdapter(api_key="test-key", model="claude-sonnet-4-20250514")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"title": "Test Anthropic"}')]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("anthropic.AsyncAnthropic", return_value=mock_client), \
         patch("anthropic.NOT_GIVEN", new=object()):
        result = await adapter.generate([
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Generate something"},
        ])

    assert result == '{"title": "Test Anthropic"}'
    mock_client.messages.create.assert_awaited_once()
