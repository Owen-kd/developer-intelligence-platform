"""AgentKnowledgeRecorder — Agent 결과 이벤트를 Knowledge 로 축적한다.

Agent 산출물(IssueTriaged/ImpactAnalyzed)은 다시 Knowledge 로 쌓여 복리로 축적된다
([.ai/architecture/knowledge-lifecycle.md]). 이 클래스는 platform 이벤트를 구독한다
(modules→platform 의존은 허용).
"""

from __future__ import annotations

from typing import cast

from dip_platform.event import Event, EventBus
from dip_platform.workflow.events import (
    IMPACT_ANALYZED,
    ISSUE_TRIAGED,
    ImpactAnalyzedPayload,
    IssueTriagedPayload,
)

from .service import PromotionService


class AgentKnowledgeRecorder:
    """Agent 결과 이벤트 → Knowledge 승격."""

    def __init__(self, promotion: PromotionService, bus: EventBus) -> None:
        self._promotion = promotion
        bus.subscribe(ISSUE_TRIAGED, self._on_triaged)
        bus.subscribe(IMPACT_ANALYZED, self._on_impact)

    async def _on_triaged(self, event: Event) -> None:
        payload = cast(IssueTriagedPayload, event.payload)
        await self._promotion.promote_agent_output(
            issue_id=payload.issue_id,
            kind="triage",
            summary=(
                f"분류: {payload.category}/{payload.priority} "
                f"(확신도 {payload.confidence:.2f}) — {payload.rationale}"
            ),
            body={
                "category": payload.category,
                "priority": payload.priority,
                "confidence": payload.confidence,
            },
            sources=("agent:triage", f"issue:{payload.issue_id}"),
        )

    async def _on_impact(self, event: Event) -> None:
        payload = cast(ImpactAnalyzedPayload, event.payload)
        await self._promotion.promote_agent_output(
            issue_id=payload.issue_id,
            kind="impact",
            summary=payload.summary,
            body={
                "impacted_shas": list(payload.impacted_shas),
                "confidence": payload.confidence,
            },
            sources=("agent:impact", f"issue:{payload.issue_id}"),
        )
