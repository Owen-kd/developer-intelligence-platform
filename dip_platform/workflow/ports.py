"""Workflow 포트 — 상위(module)가 구현해 Agent 실행에 근거를 공급한다.

platform 은 modules 를 import 하지 않으므로, 그래프 등 근거는 포트로 추상화한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ImpactEvidenceSource(ABC):
    """영향 분석 근거(그래프 관계 등)를 제공하는 포트."""

    @abstractmethod
    async def impacted_commit_shas(self, issue_id: str) -> list[str]:
        """이슈에 연결된(영향 받는) 커밋 sha 목록을 반환한다."""
