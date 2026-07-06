"""Jira 클라이언트 (포트 + 어댑터). 외부 호출은 이 infrastructure 계층에만.

- `JiraClient`: 모듈이 의존하는 **읽기 전용** 포트.
- `FakeJiraClient`: fixture 기반 어댑터(테스트/데모). 실제 Jira 연동은 [APR-002]/[APR-003]
  승인 후 `HttpJiraClient` 를 같은 포트로 추가하면 된다(모듈 코드 변경 없음).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class JiraComment:
    """Jira 코멘트 원천 DTO."""

    external_id: str
    author: str
    body: str
    created_at: str  # ISO-8601 문자열(원천 그대로)


@dataclass(frozen=True)
class JiraIssue:
    """Jira 이슈 원천 DTO."""

    key: str
    type: str
    status: str
    priority: str
    summary: str
    created_at: str
    updated_at: str
    comments: tuple[JiraComment, ...] = field(default_factory=tuple)


class JiraClient(ABC):
    """Jira 읽기 전용 포트. 구현은 외부 호출을 캡슐화한다."""

    @abstractmethod
    async def fetch_issues(self) -> list[JiraIssue]:
        """수집 대상 이슈(코멘트 포함)를 가져온다."""


_SAMPLE_ISSUES: tuple[JiraIssue, ...] = (
    JiraIssue(
        key="DIP-1",
        type="Bug",
        status="In Progress",
        priority="High",
        summary="결제 API 간헐적 타임아웃",
        created_at="2026-07-01T09:00:00+00:00",
        updated_at="2026-07-02T10:30:00+00:00",
        comments=(
            JiraComment(
                external_id="c-101",
                author="jieun",
                body="피크 시간대에 커넥션 풀이 고갈되는 것으로 보임.",
                created_at="2026-07-01T11:00:00+00:00",
            ),
            JiraComment(
                external_id="c-102",
                author="minsu",
                body="풀 사이즈 10→30 상향 후 재현 안 됨.",
                created_at="2026-07-02T10:00:00+00:00",
            ),
        ),
    ),
)


class FakeJiraClient(JiraClient):
    """fixture 기반 Jira 어댑터. 기본 샘플 또는 주입된 데이터를 반환한다."""

    def __init__(self, issues: list[JiraIssue] | None = None) -> None:
        self._issues = list(issues) if issues is not None else list(_SAMPLE_ISSUES)

    async def fetch_issues(self) -> list[JiraIssue]:
        return list(self._issues)
