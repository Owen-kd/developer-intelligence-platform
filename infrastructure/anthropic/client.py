"""실 Anthropic LLM 어댑터.

`LLMClient` 포트(infrastructure/llm)를 구현한다. 벤더 교체는 이 뒤에서 흡수되므로
platform/modules 코드는 변경되지 않는다(포트-어댑터). 정책 근거: [APR-005], [ADR-006].

주의:
- 이 계층에서만 anthropic SDK 를 호출한다(modules 직접 호출 금지).
- 프롬프트는 코드에 하드코딩하지 않는다 — 호출자(Agent)가 registry/파일에서 조립해 전달한다.
- 출력 검증(스키마/파싱)은 상위 Agent 책임. 어댑터는 모델 텍스트만 반환한다.
"""

from __future__ import annotations

from anthropic import AsyncAnthropic

from infrastructure.llm.client import LLMClient


class AnthropicClient(LLMClient):
    """Anthropic Messages API 로 단일 완성을 수행하는 어댑터."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-8",
        max_tokens: int = 1024,
    ) -> None:
        if not api_key:
            raise ValueError("Anthropic API key가 비어 있습니다 (.env ANTHROPIC_API_KEY).")
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def complete(self, system: str, user: str) -> str:
        """system/user 프롬프트로 모델 응답 텍스트를 반환한다.

        응답의 text 블록만 이어붙여 반환한다(thinking 등 비-텍스트 블록 제외).
        """
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")
