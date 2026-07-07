"""HttpJiraClient 단위 테스트 — httpx MockTransport 로 네트워크 없이 결정적 검증.

- /search/jql 응답을 JiraIssue 로 매핑(상태/우선순위/타입 name 추출).
- 코멘트 ADF 본문 → 평문, 작성자는 표시명만(PII 최소화).
- 설정 누락 시 ValueError.
"""

from __future__ import annotations

import httpx
import pytest

from infrastructure.jira.client import HttpJiraClient, _adf_to_text, _map_issue

_SEARCH_RESPONSE = {
    "issues": [
        {
            "key": "PA20-19864",
            "fields": {
                "summary": "결제 API 간헐적 타임아웃",
                "status": {"name": "In Progress"},
                "issuetype": {"name": "Bug"},
                "priority": {"name": "High"},
                "created": "2026-07-01T09:00:00.000+0900",
                "updated": "2026-07-02T10:30:00.000+0900",
                "comment": {
                    "comments": [
                        {
                            "id": "c-101",
                            "author": {"displayName": "지은", "emailAddress": "secret@x.com"},
                            "body": {
                                "type": "doc",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "커넥션 풀 고갈."}],
                                    }
                                ],
                            },
                            "created": "2026-07-01T11:00:00.000+0900",
                        }
                    ]
                },
            },
        }
    ]
}


def test_adf_to_text_extracts_plain_text() -> None:
    body = {"type": "doc", "content": [{"type": "text", "text": "hello"}]}
    assert _adf_to_text(body).strip() == "hello"


def test_map_issue_extracts_names_and_minimal_pii() -> None:
    issue = _map_issue(_SEARCH_RESPONSE["issues"][0])
    assert issue.key == "PA20-19864"
    assert issue.type == "Bug"
    assert issue.status == "In Progress"
    assert issue.priority == "High"
    assert issue.comments[0].author == "지은"  # 표시명만
    assert "secret@x.com" not in issue.comments[0].author  # 이메일 미저장
    assert issue.comments[0].body == "커넥션 풀 고갈."


@pytest.mark.asyncio
async def test_fetch_issues_via_mock_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["jql"] = request.url.params.get("jql", "")
        return httpx.Response(200, json=_SEARCH_RESPONSE)

    real_async_client = httpx.AsyncClient

    def _client_with_mock(**kwargs: object) -> httpx.AsyncClient:
        kwargs.pop("auth", None)
        return real_async_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "AsyncClient", _client_with_mock)

    client = HttpJiraClient("https://x.atlassian.net", "e@x.com", "tok", "PA20", max_issues=5)
    issues = await client.fetch_issues()

    assert captured["path"] == "/rest/api/3/search/jql"
    assert "project=PA20" in captured["jql"]
    assert issues[0].key == "PA20-19864"


def test_missing_config_raises() -> None:
    with pytest.raises(ValueError):
        HttpJiraClient("", "e", "t", "P")
