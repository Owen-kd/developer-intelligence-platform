"""AnthropicClient 어댑터 단위 테스트.

실제 네트워크 호출 없이 SDK 를 목킹한다(결정적). 검증 포인트:
- text 블록만 이어붙여 반환한다(비-텍스트 블록 무시).
- 포트 계약대로 (system, user) 를 messages.create 로 전달한다.
- 빈 API 키는 ValueError.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from infrastructure.anthropic.client import AnthropicClient


def _block(block_type: str, text: str = "") -> SimpleNamespace:
    return SimpleNamespace(type=block_type, text=text)


@pytest.mark.asyncio
async def test_complete_joins_text_blocks_only() -> None:
    fake_response = SimpleNamespace(
        content=[_block("thinking"), _block("text", '{"category"'), _block("text", ':"bug"}')]
    )
    with patch("infrastructure.anthropic.client.AsyncAnthropic") as mock_ctor:
        mock_client = mock_ctor.return_value
        mock_client.messages = SimpleNamespace(create=AsyncMock(return_value=fake_response))

        client = AnthropicClient(api_key="sk-test", model="claude-opus-4-8", max_tokens=512)
        result = await client.complete(system="분류기", user="이슈 본문")

    assert result == '{"category":"bug"}'  # 비-텍스트 블록은 제외됨

    kwargs: dict[str, Any] = mock_client.messages.create.await_args.kwargs
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["max_tokens"] == 512
    assert kwargs["system"] == "분류기"
    assert kwargs["messages"] == [{"role": "user", "content": "이슈 본문"}]


def test_empty_api_key_raises() -> None:
    with pytest.raises(ValueError):
        AnthropicClient(api_key="")
