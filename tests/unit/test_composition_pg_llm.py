"""composition_pg 의 LLM 팩토리 단위 테스트 (오프라인, DB/네트워크 無).

- 키가 없으면 결정적 FakeLLMClient 로 폴백한다(데모/CI 안전).
- 키가 있으면 실 AnthropicClient 를 만든다(생성만; 호출하지 않음).
"""

from __future__ import annotations

from apps.composition_pg import _build_llm
from infrastructure.anthropic.client import AnthropicClient
from infrastructure.llm.client import FakeLLMClient
from shared.config.settings import Settings


def test_build_llm_falls_back_to_fake_without_key() -> None:
    settings = Settings(anthropic_api_key="")
    triage, impact = _build_llm(settings)

    assert isinstance(triage, FakeLLMClient)
    assert isinstance(impact, FakeLLMClient)


def test_build_llm_uses_anthropic_with_key() -> None:
    settings = Settings(anthropic_api_key="sk-test", anthropic_model="claude-opus-4-8")
    triage, impact = _build_llm(settings)

    assert isinstance(triage, AnthropicClient)
    assert triage is impact  # 실 모드에서는 단일 클라이언트를 공유
