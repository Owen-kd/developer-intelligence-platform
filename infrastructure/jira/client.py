"""Jira 클라이언트 (포트 + 어댑터). 외부 호출은 이 infrastructure 계층에만.

- `JiraClient`: 모듈이 의존하는 **읽기 전용** 포트.
- `FakeJiraClient`: fixture 기반 어댑터(테스트/데모). 실제 Jira 연동은 [APR-002]/[APR-003]
  승인 후 `HttpJiraClient` 를 같은 포트로 추가하면 된다(모듈 코드 변경 없음).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from shared.config.settings import get_settings
from shared.logger import get_logger

_logger = get_logger("jira.client")


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


def _adf_to_text(node: Any) -> str:
    """Atlassian Document Format(코멘트 body) 를 평문으로 평탄화한다.

    블록 노드(paragraph/heading/listItem)는 한 줄로, 컨테이너는 블록들을 줄바꿈으로 잇는다.
    """
    if isinstance(node, dict):
        node_type = node.get("type")
        if node_type == "text":
            return str(node.get("text", ""))
        parts = [_adf_to_text(child) for child in node.get("content", [])]
        parts = [part for part in parts if part]
        if node_type in {"paragraph", "heading", "listItem"}:
            return "".join(parts)  # 블록 내부 inline 은 이어붙인다
        return "\n".join(parts)  # 컨테이너는 블록을 줄바꿈으로
    if isinstance(node, list):
        return "\n".join(_adf_to_text(child) for child in node)
    return ""


def _name(field_value: Any) -> str:
    return str((field_value or {}).get("name", "")) if isinstance(field_value, dict) else ""


class HttpJiraClient(JiraClient):
    """실 Jira Cloud REST v3 어댑터(읽기 전용). 외부 호출은 이 계층에만 존재한다."""

    _SEARCH = "/rest/api/3/search/jql"
    _FIELDS = "summary,issuetype,status,priority,created,updated"

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str,
        limit: int | None = None,
        page_size: int = 50,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._auth = (email, api_token)
        self._project = project_key
        self._limit = limit
        self._page_size = page_size

    async def fetch_issues(self) -> list[JiraIssue]:
        issues: list[JiraIssue] = []
        async with httpx.AsyncClient(
            base_url=self._base, auth=self._auth, timeout=30.0
        ) as client:
            next_token: str | None = None
            while True:
                params: dict[str, str | int] = {
                    "jql": f"project={self._project} ORDER BY created DESC",
                    "maxResults": self._page_size,
                    "fields": self._FIELDS,
                }
                if next_token:
                    params["nextPageToken"] = next_token
                resp = await client.get(self._SEARCH, params=params)
                resp.raise_for_status()
                data = resp.json()

                for raw in data.get("issues", []):
                    if self._limit is not None and len(issues) >= self._limit:
                        break
                    issues.append(await self._to_issue(client, raw))

                reached_limit = self._limit is not None and len(issues) >= self._limit
                if reached_limit or data.get("isLast") or not data.get("nextPageToken"):
                    break
                next_token = data["nextPageToken"]

        _logger.info("jira.fetch.done", project=self._project, issues=len(issues))
        return issues

    async def _to_issue(self, client: httpx.AsyncClient, raw: dict[str, Any]) -> JiraIssue:
        fields = raw.get("fields", {})
        key = str(raw["key"])
        comments = await self._fetch_comments(client, key)
        return JiraIssue(
            key=key,
            type=_name(fields.get("issuetype")),
            status=_name(fields.get("status")),
            priority=_name(fields.get("priority")),
            summary=str(fields.get("summary", "")),
            created_at=str(fields.get("created", "")),
            updated_at=str(fields.get("updated", "")),
            comments=comments,
        )

    async def _fetch_comments(
        self, client: httpx.AsyncClient, issue_key: str
    ) -> tuple[JiraComment, ...]:
        resp = await client.get(
            f"/rest/api/3/issue/{issue_key}/comment", params={"maxResults": 50}
        )
        if resp.status_code != 200:
            return ()
        result: list[JiraComment] = []
        for comment in resp.json().get("comments", []):
            author = comment.get("author") or {}
            result.append(
                JiraComment(
                    external_id=str(comment["id"]),
                    author=str(author.get("displayName", "")),
                    body=_adf_to_text(comment.get("body")),
                    created_at=str(comment.get("created", "")),
                )
            )
        return tuple(result)


def http_client_from_settings(limit: int | None = None) -> HttpJiraClient:
    """중앙 설정(.env)으로 실 Jira 클라이언트를 조립한다."""
    settings = get_settings()
    return HttpJiraClient(
        base_url=settings.jira_base_url,
        email=settings.jira_email,
        api_token=settings.jira_api_token,
        project_key=settings.jira_project_key,
        limit=limit,
    )
