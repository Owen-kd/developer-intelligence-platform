"""Jira 도메인 이벤트 페이로드.

이름은 과거형 PascalCase, 페이로드는 불변 + 식별자 최소([.ai/contracts/event-contract.md]).
"""

from __future__ import annotations

from dataclasses import dataclass

from dip_platform.event import EventPayload

ISSUE_CREATED = "IssueCreated"
COMMENT_ADDED = "CommentAdded"


@dataclass(frozen=True)
class IssueCreatedPayload(EventPayload):
    """이슈가 수집·적재되었다."""

    issue_id: str
    jira_key: str


@dataclass(frozen=True)
class CommentAddedPayload(EventPayload):
    """이슈에 코멘트가 적재되었다."""

    issue_id: str
    jira_key: str
    comment_external_id: str
