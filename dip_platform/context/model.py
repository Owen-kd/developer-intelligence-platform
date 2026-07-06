"""Context 모델 + KnowledgeSource 포트.

platform 은 modules 아래 계층이므로 특정 모듈을 import 하지 않는다.
Knowledge 조회는 이 포트로 추상화하고, 구현(어댑터)은 상위(module/apps)에서 제공한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeItem:
    """Context 에 담기는 지식 조각(플랫폼 표현). 원천 데이터가 아니라 Knowledge 다."""

    knowledge_id: str
    summary: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class BudgetMeta:
    """토큰 예산 소비 메타(관측/재현용)."""

    token_budget: int
    tokens_used: int
    items_considered: int
    items_included: int


@dataclass(frozen=True)
class Context:
    """Agent 가 소비하는 조립된 컨텍스트. 프롬프트는 포함하지 않는다."""

    task: str
    target: str
    knowledge: tuple[KnowledgeItem, ...]
    sources: tuple[str, ...]
    budget_meta: BudgetMeta


class KnowledgeSource(ABC):
    """(task, target)에 관련된 Knowledge 를 제공하는 포트."""

    @abstractmethod
    async def fetch(self, task: str, target_id: str) -> list[KnowledgeItem]:
        """대상과 관련된 KnowledgeItem 목록을 반환한다."""
