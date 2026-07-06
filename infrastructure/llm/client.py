"""벤더 중립 LLM 포트 + Fake 어댑터.

- `LLMClient`: 모듈/플랫폼이 의존하는 포트. 벤더 교체는 이 뒤에서 흡수된다.
- `FakeLLMClient`: 결정적 어댑터(테스트/데모). 실제 OpenAI/Anthropic 어댑터는 같은 포트로
  `infrastructure/openai`·`infrastructure/anthropic` 에 추가한다([APR-005]: 외부 전송/비용 정책).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


class LLMClient(ABC):
    """단일 완성(completion) 호출 포트."""

    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """system/user 프롬프트로 모델 응답 문자열을 반환한다."""


class FakeLLMClient(LLMClient):
    """결정적 Fake LLM.

    `responder` 가 주어지면 (system, user)->str 로 응답을 만들고,
    없으면 고정 `response` 를 반환한다.
    """

    def __init__(
        self,
        response: str = "{}",
        responder: Callable[[str, str], str] | None = None,
    ) -> None:
        self._response = response
        self._responder = responder

    async def complete(self, system: str, user: str) -> str:
        if self._responder is not None:
            return self._responder(system, user)
        return self._response
