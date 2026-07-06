"""Report API 테스트 — /issues, /impact-analyses + 인증(Bearer)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

_AUTH = {"Authorization": "Bearer dev-token"}


def test_list_issues_returns_collected_issue() -> None:
    with TestClient(app) as client:
        resp = client.get("/issues", headers=_AUTH)
        assert resp.status_code == 200
        issues = resp.json()
        assert any(issue["jira_key"] == "DIP-1" for issue in issues)


def test_issue_detail_includes_agent_knowledge() -> None:
    with TestClient(app) as client:
        resp = client.get("/issues/DIP-1", headers=_AUTH)
        assert resp.status_code == 200
        body = resp.json()
        types = {item["type"] for item in body["knowledge"]}
        # 원천 요약 + 분류 + 영향도 지식이 축적되어 있어야 한다.
        assert {"issue_summary", "triage", "impact"} <= types
        # 모든 Knowledge 는 출처를 가진다.
        assert all(item["sources"] for item in body["knowledge"])


def test_issue_detail_404_for_unknown() -> None:
    with TestClient(app) as client:
        assert client.get("/issues/NOPE-1", headers=_AUTH).status_code == 404


def test_list_impact_analyses() -> None:
    with TestClient(app) as client:
        resp = client.get("/impact-analyses", headers=_AUTH)
        assert resp.status_code == 200
        analyses = resp.json()
        assert len(analyses) >= 1
        assert analyses[0]["summary"]


def test_requires_auth() -> None:
    with TestClient(app) as client:
        assert client.get("/issues").status_code == 401
        assert client.get("/issues", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_access_is_audited() -> None:
    with TestClient(app) as client:
        client.get("/issues", headers=_AUTH)
        client.get("/issues")  # 실패(401)
        actions = [entry.action for entry in app.state.dip.audit.entries]
        assert "api.access" in actions
        assert "api.auth_failed" in actions
