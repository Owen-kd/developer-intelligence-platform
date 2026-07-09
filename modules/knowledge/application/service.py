"""PromotionService — Event/Timeline 을 Knowledge 로 승격한다(승격 1).

규칙 기반 승격(LLM 미사용)이며 다음 불변식을 강제한다:
- 모든 Knowledge 는 출처(sources)를 가진다.
- 저장 전 스키마 검증을 통과해야 한다.
- 승격은 append(기존 Knowledge/Event 를 파괴하지 않는다).
"""

from __future__ import annotations

import uuid

from dip_platform.event import Event, EventBus
from modules.knowledge.domain.entity import IssueSnapshot, Knowledge
from modules.knowledge.domain.events import KNOWLEDGE_PROMOTED, KnowledgePromotedPayload
from modules.knowledge.domain.repository import IssueSourceReader, KnowledgeRepository
from shared.exceptions import NotFoundError, ValidationError
from shared.logger import get_logger

_logger = get_logger("knowledge.promotion")

_KNOWLEDGE_TYPE = "issue_summary"


def _build_summary(snapshot: IssueSnapshot) -> str:
    who = f", 담당 {snapshot.assignee}" if snapshot.assignee else ""
    shelf = f" [서가: {', '.join(snapshot.components)}]" if snapshot.components else ""
    return (
        f"{snapshot.jira_key} ({snapshot.status}/{snapshot.priority}): {snapshot.summary}{shelf} "
        f"— 코멘트 {len(snapshot.comments)}건, 링크된 커밋 {len(snapshot.commit_shas)}건{who}."
    )


def _derive_sources(snapshot: IssueSnapshot) -> tuple[str, ...]:
    # 출처는 승격에 사용된 Event id 를 우선한다.
    # (없으면 원천 식별자로라도 provenance 를 보존해 불변식을 만족시킨다.)
    if snapshot.source_event_ids:
        return snapshot.source_event_ids
    return (f"issue:{snapshot.jira_key}", *(f"commit:{sha}" for sha in snapshot.commit_shas))


def _validate(knowledge: Knowledge) -> None:
    if not knowledge.summary.strip():
        raise ValidationError("Knowledge summary 가 비어 있다")
    if not knowledge.sources:
        raise ValidationError("Knowledge 는 출처(sources)를 가져야 한다")


class PromotionService:
    """이슈 스냅샷을 Knowledge 로 승격한다."""

    def __init__(
        self,
        reader: IssueSourceReader,
        repo: KnowledgeRepository,
        bus: EventBus,
    ) -> None:
        self._reader = reader
        self._repo = repo
        self._bus = bus

    async def promote_issue(self, issue_id: str) -> Knowledge:
        snapshot = await self._reader.get_snapshot(issue_id)
        if snapshot is None:
            raise NotFoundError(f"이슈 스냅샷을 찾을 수 없다: {issue_id}")

        knowledge = Knowledge(
            id=str(uuid.uuid4()),
            type=_KNOWLEDGE_TYPE,
            issue_id=snapshot.issue_id,
            summary=_build_summary(snapshot),
            body={
                "jira_key": snapshot.jira_key,
                "status": snapshot.status,
                "priority": snapshot.priority,
                "assignee": snapshot.assignee,
                "reporter": snapshot.reporter,
                "description": snapshot.description,  # 본문(원천, 2차 LLM 요약용)
                "labels": list(snapshot.labels),
                "components": list(snapshot.components),  # 서가
                "comments": list(snapshot.comments),
                "commit_shas": list(snapshot.commit_shas),
            },
            sources=_derive_sources(snapshot),
        )
        _validate(knowledge)  # 검증 통과분만 저장한다.

        await self._save_and_announce(knowledge)
        return knowledge

    async def promote_agent_output(
        self,
        issue_id: str,
        kind: str,
        summary: str,
        body: dict[str, object],
        sources: tuple[str, ...],
    ) -> Knowledge:
        """Agent 산출물(분류/영향도 등)을 Knowledge 로 축적한다(AI 출력 → 검증 → 지식)."""
        knowledge = Knowledge(
            id=str(uuid.uuid4()),
            type=kind,
            issue_id=issue_id,
            summary=summary,
            body=body,
            sources=sources,
        )
        _validate(knowledge)
        await self._save_and_announce(knowledge)
        return knowledge

    async def _save_and_announce(self, knowledge: Knowledge) -> None:
        await self._repo.save(knowledge)
        await self._bus.publish(
            Event(
                KNOWLEDGE_PROMOTED,
                KnowledgePromotedPayload(knowledge.id, knowledge.issue_id, knowledge.type),
            )
        )
        _logger.info(
            "knowledge.promoted",
            knowledge_id=knowledge.id,
            issue_id=knowledge.issue_id,
            type=knowledge.type,
            sources=len(knowledge.sources),
        )
