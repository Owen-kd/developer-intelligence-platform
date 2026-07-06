"""IncidentPromotionService — Knowledge → Incident Library(승격 2).

근본원인은 반드시 사실 근거(Knowledge)에 연결한다. 근거가 없으면 승격하지 않는다.
Promotion 은 append(파괴 금지).
"""

from __future__ import annotations

import uuid

from dip_platform.event import Event, EventBus
from modules.incident.domain.entity import Incident, KnowledgeRef
from modules.incident.domain.events import INCIDENT_PROMOTED, IncidentPromotedPayload
from modules.incident.domain.repository import IncidentRepository, KnowledgeReader
from shared.exceptions import ValidationError
from shared.logger import get_logger

_logger = get_logger("incident.promotion")


def _pick(refs: list[KnowledgeRef], type_: str) -> KnowledgeRef | None:
    return next((ref for ref in refs if ref.type == type_), None)


class IncidentPromotionService:
    """이슈의 Knowledge 를 근거로 Incident 를 조립한다."""

    def __init__(
        self,
        reader: KnowledgeReader,
        repo: IncidentRepository,
        bus: EventBus,
    ) -> None:
        self._reader = reader
        self._repo = repo
        self._bus = bus

    async def promote(self, issue_id: str) -> Incident:
        refs = await self._reader.refs_by_issue(issue_id)
        if not refs:
            raise ValidationError(f"근거 Knowledge 가 없어 Incident 승격 불가: {issue_id}")

        summary_ref = _pick(refs, "issue_summary")
        impact_ref = _pick(refs, "impact")

        root_cause = summary_ref.summary if summary_ref is not None else refs[0].summary
        resolution = (
            impact_ref.summary if impact_ref is not None else "해결 내역 미확정(추가 근거 필요)"
        )

        incident = Incident(
            id=str(uuid.uuid4()),
            issue_id=issue_id,
            root_cause=root_cause,
            resolution=resolution,
            prevention="동일 근본원인 재발 방지: 관련 지표 모니터링 및 회귀 테스트 추가",
            sources=tuple(ref.id for ref in refs),  # 사실 근거(Knowledge id) 보존
        )
        await self._repo.save(incident)
        await self._bus.publish(
            Event(INCIDENT_PROMOTED, IncidentPromotedPayload(incident.id, issue_id))
        )
        _logger.info(
            "incident.promoted",
            incident_id=incident.id,
            issue_id=issue_id,
            sources=len(incident.sources),
        )
        return incident
