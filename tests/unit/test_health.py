"""헬스 엔드포인트 스모크 테스트.

Postgres 가 없어도(ping 실패) 앱은 200 을 반환하고 status=degraded 로 응답해야 한다.
"""

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200

    body = resp.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["version"] == "0.1.0"
    assert "postgres" in body["dependencies"]
