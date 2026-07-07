"""Jira 클라이언트 (포트 + 어댑터). 외부 호출은 이 infrastructure 계층에만.

- `JiraClient`: 모듈이 의존하는 **읽기 전용** 포트.
- `FakeJiraClient`: fixture 기반 어댑터(테스트/데모). 실제 Jira 연동은 [APR-002]/[APR-003]
  승인 후 `HttpJiraClient` 를 같은 포트로 추가하면 된다(모듈 코드 변경 없음).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field

import httpx


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
    assignee: str = ""  # 담당자 표시명(PII 최소화)
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
        assignee="민수",
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


def _adf_to_text(node: object) -> str:
    """Atlassian Document Format(ADF) 트리에서 평문을 추출한다(코멘트 본문용)."""
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return str(node.get("text", ""))
    content = node.get("content")
    inner = "".join(_adf_to_text(c) for c in content) if isinstance(content, list) else ""
    block = {"paragraph", "heading", "listItem", "blockquote", "codeBlock"}
    return inner + "\n" if node.get("type") in block else inner


def _named(fields: Mapping[str, object], key: str) -> str:
    value = fields.get(key)
    return str(value["name"]) if isinstance(value, dict) and value.get("name") else "Unknown"


def _map_issue(raw: Mapping[str, object]) -> JiraIssue:
    fields_obj = raw.get("fields", {})
    fields: Mapping[str, object] = fields_obj if isinstance(fields_obj, dict) else {}

    comment_field = fields.get("comment")
    raw_comments = comment_field.get("comments", []) if isinstance(comment_field, dict) else []
    comments = tuple(
        JiraComment(
            external_id=str(c.get("id", "")),
            # PII 최소화: 작성자는 표시명만 저장(이메일/계정ID 미저장) — APR-002
            author=str((c.get("author") or {}).get("displayName", "unknown")),
            body=_adf_to_text(c.get("body")).strip(),
            created_at=str(c.get("created", "")),
        )
        for c in raw_comments
        if isinstance(c, dict)
    )
    assignee_obj = fields.get("assignee")
    assignee = str(assignee_obj["displayName"]) if isinstance(assignee_obj, dict) else ""

    return JiraIssue(
        key=str(raw.get("key", "")),
        type=_named(fields, "issuetype"),
        status=_named(fields, "status"),
        priority=_named(fields, "priority"),
        summary=str(fields.get("summary", "")),
        created_at=str(fields.get("created", "")),
        updated_at=str(fields.get("updated", "")),
        assignee=assignee,  # PII 최소화: 표시명만
        comments=comments,
    )


class HttpJiraClient(JiraClient):
    """실 Jira Cloud REST v3 읽기 전용 어댑터([APR-002], [ADR-007]).

    Enhanced JQL 검색(`/search/jql`)을 사용한다(classic `/search` 는 410 Gone).
    수집은 bounded(최근 N개) — 전량 증분 동기화는 후속 과제.
    """

    _FIELDS = "summary,status,issuetype,priority,created,updated,assignee,comment"
    _PAGE_SIZE = 100  # /search/jql 페이지 상한

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str,
        max_issues: int = 10,
    ) -> None:
        if not (base_url and email and api_token and project_key):
            raise ValueError("Jira 설정이 비어 있습니다 (.env JIRA_*).")
        self._base = base_url.rstrip("/")
        self._auth = httpx.BasicAuth(email, api_token)
        self._jql = f"project={project_key} ORDER BY created DESC"
        self._max = max_issues

    async def fetch_issues(self) -> list[JiraIssue]:
        """max_issues 에 도달하거나 마지막 페이지까지 nextPageToken 으로 순회한다."""
        collected: list[JiraIssue] = []
        token: str | None = None
        async with httpx.AsyncClient(auth=self._auth, timeout=30.0) as client:
            while len(collected) < self._max:
                params: dict[str, str | int] = {
                    "jql": self._jql,
                    "maxResults": min(self._PAGE_SIZE, self._max - len(collected)),
                    "fields": self._FIELDS,
                }
                if token:
                    params["nextPageToken"] = token
                resp = await client.get(
                    f"{self._base}/rest/api/3/search/jql",
                    params=params,
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, dict):
                    break
                page = [_map_issue(r) for r in data.get("issues", []) if isinstance(r, dict)]
                collected.extend(page)
                token = data.get("nextPageToken")
                if data.get("isLast", True) or not token or not page:
                    break
        return collected[: self._max]
