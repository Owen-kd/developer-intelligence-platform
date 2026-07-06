"""ContextBuilder — Knowledge 로부터 결정적으로 Context 를 조립한다.

규칙([.ai/architecture/context-engine.md]):
- 입력이 같으면 출력도 같다(재현성) → 안정 정렬 + 결정적 토큰 추정.
- 토큰 예산을 존중하고, 출처를 보존한다.
- 원천 데이터가 아니라 Knowledge 만 담는다. 프롬프트는 섞지 않는다.
"""

from __future__ import annotations

from shared.constants import CHARS_PER_TOKEN, DEFAULT_TOKEN_BUDGET
from shared.logger import get_logger

from .model import BudgetMeta, Context, KnowledgeItem, KnowledgeSource

_logger = get_logger("context.builder")


def estimate_tokens(text: str) -> int:
    """문자 수 기반의 결정적 토큰 추정(하한 1)."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def _rank(items: list[KnowledgeItem]) -> list[KnowledgeItem]:
    # 결정적 정렬: knowledge_id 오름차순(재현성 보장).
    return sorted(items, key=lambda item: item.knowledge_id)


class ContextBuilder:
    """KnowledgeSource 를 통해 Context 를 조립한다."""

    def __init__(self, source: KnowledgeSource, token_budget: int = DEFAULT_TOKEN_BUDGET) -> None:
        self._source = source
        self._token_budget = token_budget

    async def build(self, task: str, target_id: str) -> Context:
        candidates = _rank(await self._source.fetch(task, target_id))

        included: list[KnowledgeItem] = []
        sources: list[str] = []
        tokens_used = 0
        for item in candidates:
            cost = estimate_tokens(item.summary)
            if tokens_used + cost > self._token_budget and included:
                break  # 예산 초과 — 신호 우선(정렬 상위)만 담고 절삭
            tokens_used += cost
            included.append(item)
            for source in item.sources:
                if source not in sources:
                    sources.append(source)

        context = Context(
            task=task,
            target=target_id,
            knowledge=tuple(included),
            sources=tuple(sources),
            budget_meta=BudgetMeta(
                token_budget=self._token_budget,
                tokens_used=tokens_used,
                items_considered=len(candidates),
                items_included=len(included),
            ),
        )
        _logger.info(
            "context.built",
            task=task,
            target=target_id,
            considered=len(candidates),
            included=len(included),
            tokens=tokens_used,
        )
        return context
