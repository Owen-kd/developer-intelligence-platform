"""Agent 산출 이벤트 페이로드.

Agent 결과는 Event 로 발행되어 다시 Knowledge 로 축적된다([knowledge-lifecycle]).
"""

from __future__ import annotations

from dataclasses import dataclass

from dip_platform.event import EventPayload

ISSUE_TRIAGED = "IssueTriaged"
IMPACT_ANALYZED = "ImpactAnalyzed"


@dataclass(frozen=True)
class IssueTriagedPayload(EventPayload):
    """이슈가 분류되었다."""

    issue_id: str
    category: str
    priority: str
    confidence: float
    rationale: str


@dataclass(frozen=True)
class ImpactAnalyzedPayload(EventPayload):
    """이슈 영향도가 분석되었다."""

    issue_id: str
    summary: str
    impacted_shas: tuple[str, ...]
    confidence: float
