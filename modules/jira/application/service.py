"""JiraService — 수집 유스케이스.

흐름: JiraClient(원천) → 도메인 매핑 → Repository(멱등 upsert) → EventBus(사실 전파).
재실행해도 중복 적재/중복 이벤트가 없도록 신규 여부를 판별해 발행한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from dip_platform.event import Event, EventBus
from infrastructure.jira.client import JiraClient, JiraIssue
from modules.jira.domain.entity import Comment, Issue
from modules.jira.domain.events import (
    COMMENT_ADDED,
    ISSUE_CREATED,
    CommentAddedPayload,
    IssueCreatedPayload,
)
from modules.jira.domain.repository import IssueRepository
from shared.logger import get_logger

_logger = get_logger("jira.service")


@dataclass(frozen=True)
class SyncResult:
    """동기화 1회 결과 요약."""

    issues_synced: int
    issues_created: int
    comments_added: int


def _to_issue(raw: JiraIssue) -> Issue:
    return Issue(
        jira_key=raw.key,
        type=raw.type,
        status=raw.status,
        priority=raw.priority,
        summary=raw.summary,
        created_at=raw.created_at,
        updated_at=raw.updated_at,
        comments=[
            Comment(
                external_id=comment.external_id,
                author=comment.author,
                body=comment.body,
                created_at=comment.created_at,
            )
            for comment in raw.comments
        ],
    )


class JiraService:
    """Jira 수집을 오케스트레이션하는 애플리케이션 서비스."""

    def __init__(self, client: JiraClient, repo: IssueRepository, bus: EventBus) -> None:
        self._client = client
        self._repo = repo
        self._bus = bus

    async def sync(self) -> SyncResult:
        raw_issues = await self._client.fetch_issues()
        issues_created = 0
        comments_added = 0

        for raw in raw_issues:
            issue = _to_issue(raw)
            existed = await self._repo.get_issue(issue.jira_key) is not None
            issue_id = await self._repo.upsert_issue(issue)

            if not existed:
                issues_created += 1
                await self._bus.publish(
                    Event(ISSUE_CREATED, IssueCreatedPayload(issue_id, issue.jira_key))
                )

            for comment in issue.comments:
                is_new = await self._repo.upsert_comment(issue_id, issue.jira_key, comment)
                if is_new:
                    comments_added += 1
                    await self._bus.publish(
                        Event(
                            COMMENT_ADDED,
                            CommentAddedPayload(issue_id, issue.jira_key, comment.external_id),
                        )
                    )

        result = SyncResult(
            issues_synced=len(raw_issues),
            issues_created=issues_created,
            comments_added=comments_added,
        )
        _logger.info(
            "jira.sync.done",
            issues_synced=result.issues_synced,
            issues_created=result.issues_created,
            comments_added=result.comments_added,
        )
        return result
