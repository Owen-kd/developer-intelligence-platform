"""증분 수집 JQL(updated_since) 단위 테스트 — HttpJiraClient._build_jql."""

from __future__ import annotations

from infrastructure.jira.client import FakeJiraClient, HttpJiraClient


def _client() -> HttpJiraClient:
    return HttpJiraClient(
        base_url="https://x.atlassian.net",
        email="e@x.com",
        api_token="tok",
        project_key="PA20",
        max_issues=50,
    )


def test_full_jql_when_no_cursor() -> None:
    assert _client()._build_jql(None) == "project=PA20 ORDER BY created DESC"


def test_incremental_jql_filters_updated_and_orders_asc() -> None:
    jql = _client()._build_jql("2026-07-08 02:00")
    assert 'updated >= "2026-07-08 02:00"' in jql
    assert "ORDER BY updated ASC" in jql
    assert jql.startswith("project=PA20 AND")


async def test_fake_client_ignores_cursor() -> None:
    client = FakeJiraClient()
    full = await client.fetch_issues()
    incremental = await client.fetch_issues("2026-07-08 02:00")
    assert [i.key for i in full] == [i.key for i in incremental]
