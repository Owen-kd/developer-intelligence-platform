"""Knowledge 도메인 이벤트 페이로드."""

from __future__ import annotations

from dataclasses import dataclass

from dip_platform.event import EventPayload

KNOWLEDGE_PROMOTED = "KnowledgePromoted"
ISSUE_CLASSIFIED = "IssueClassified"


@dataclass(frozen=True)
class KnowledgePromotedPayload(EventPayload):
    """Event/Timeline 이 Knowledge 로 승격되었다."""

    knowledge_id: str
    issue_id: str
    knowledge_type: str


@dataclass(frozen=True)
class IssueClassifiedPayload(EventPayload):
    """이슈가 facet(도메인/기능영역/액션/채널/유형/팀·영역)으로 분류되었다 — ADR-015."""

    issue_id: str
    jira_key: str
    domain: str
    channel: str
    method: str  # 'rule' | 'llm'
