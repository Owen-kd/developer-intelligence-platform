"""Agent 계약 — 파이프라인의 마지막 단계(AI Last).

Agent 는 조립된 Context 안에서만 추론하고, 검증 가능한 구조로 결과를 반환한다
([.ai/contracts/agent-contract.md]).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from dip_platform.context import Context


@dataclass(frozen=True)
class AgentResult:
    """Agent 산출물 — 판정 + 근거 + 확신도."""

    kind: str
    output: dict[str, object]
    confidence: float
    rationale: str


class Agent(ABC):
    """하나의 판단 작업을 수행하는 Agent."""

    name: str

    @abstractmethod
    async def run(self, context: Context) -> AgentResult:
        """Context 를 받아 구조화된 결과를 반환한다."""
