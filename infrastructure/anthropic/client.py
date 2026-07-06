"""실 Anthropic LLM 어댑터 (LLMClient 포트). 외부 호출은 이 계층에만.

같은 포트를 만족하므로 Agent/워크플로 코드는 fake 와 동일하게 동작한다.
토큰 사용량을 기록해 비용 산출에 쓴다([APR-005] 데이터/비용 정책).
"""

from __future__ import annotations

from anthropic import AsyncAnthropic

from infrastructure.llm.client import LLMClient
from shared.config.settings import get_settings
from shared.logger import get_logger

_logger = get_logger("anthropic.client")

# 참고 단가(USD / 1M tokens) — 비용 산출용.
_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
}

_MAX_TOKENS = 400


class AnthropicClient(LLMClient):
    """Anthropic Messages API 어댑터."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self._model = model or settings.anthropic_model
        self._client = AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)
        self.last_input_tokens = 0
        self.last_output_tokens = 0

    @property
    def model(self) -> str:
        return self._model

    async def complete(self, system: str, user: str) -> str:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        self.last_input_tokens = resp.usage.input_tokens
        self.last_output_tokens = resp.usage.output_tokens
        _logger.info(
            "anthropic.completed",
            model=self._model,
            input_tokens=self.last_input_tokens,
            output_tokens=self.last_output_tokens,
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return text

    def last_cost_usd(self) -> float:
        """직전 호출의 대략적 비용(USD)."""
        in_rate, out_rate = _PRICING.get(self._model, (0.0, 0.0))
        return self.last_input_tokens / 1e6 * in_rate + self.last_output_tokens / 1e6 * out_rate
