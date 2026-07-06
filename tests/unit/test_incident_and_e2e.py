"""Incident 승격 + 전체 파이프라인 e2e 테스트."""

from __future__ import annotations

import pytest

from apps.composition import build_and_run
from dip_platform.event import InMemoryEventBus
from modules.incident.application.service import IncidentPromotionService
from modules.incident.domain.entity import KnowledgeRef
from modules.incident.domain.repository import KnowledgeReader
from modules.incident.infrastructure.repository import InMemoryIncidentRepository
from shared.exceptions import ValidationError


class _StubReader(KnowledgeReader):
    def __init__(self, refs: list[KnowledgeRef]) -> None:
        self._refs = refs

    async def refs_by_issue(self, issue_id: str) -> list[KnowledgeRef]:
        return list(self._refs)


async def test_incident_requires_factual_grounding() -> None:
    service = IncidentPromotionService(
        _StubReader([]), InMemoryIncidentRepository(), InMemoryEventBus()
    )
    with pytest.raises(ValidationError):
        await service.promote("i-1")


async def test_incident_preserves_sources() -> None:
    refs = [
        KnowledgeRef("k-1", "issue_summary", "DIP-1 결제 타임아웃 요약"),
        KnowledgeRef("k-2", "impact", "결제 경로 영향"),
    ]
    repo = InMemoryIncidentRepository()
    service = IncidentPromotionService(_StubReader(refs), repo, InMemoryEventBus())

    incident = await service.promote("i-1")

    assert incident.sources == ("k-1", "k-2")  # 사실 근거 보존
    assert "결제" in incident.root_cause


async def test_full_pipeline_accumulates_knowledge_and_incident() -> None:
    app = await build_and_run()

    issues = await app.issue_repo.list_issues()
    assert len(issues) == 1
    issue = issues[0]
    assert issue.id is not None

    knowledge = await app.knowledge_repo.list_by_issue(issue.id)
    types = {item.type for item in knowledge}
    # 원천요약 + 분류 + 영향도가 모두 축적된다.
    assert {"issue_summary", "triage", "impact"} <= types

    incidents = await app.incident_repo.list_all()
    assert len(incidents) == 1
    assert incidents[0].sources  # Incident 는 근거를 가진다

    # 감사 로그에 Agent step 이 남는다.
    assert any(entry.action.startswith("agent.step") for entry in app.audit.entries)
