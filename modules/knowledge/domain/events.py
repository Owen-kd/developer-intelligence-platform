"""Knowledge 도메인 이벤트 페이로드."""

from __future__ import annotations

from dataclasses import dataclass

from dip_platform.event import EventPayload

KNOWLEDGE_PROMOTED = "KnowledgePromoted"


@dataclass(frozen=True)
class KnowledgePromotedPayload(EventPayload):
    """Event/Timeline 이 Knowledge 로 승격되었다."""

    knowledge_id: str
    issue_id: str
    knowledge_type: str
