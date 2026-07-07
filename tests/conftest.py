"""공용 pytest 픽스처.

테스트 격리: `infrastructure/postgres/connection.py` 는 async 엔진을 모듈 전역 싱글턴으로
캐시한다. 여러 테스트가 각자 다른 이벤트 루프에서 `TestClient(app)` lifespan 을 실행하면,
한 테스트의 루프에서 만들어진 전역 엔진을 다른 테스트의 루프에서 `dispose()` 하다가
SQLAlchemy greenlet 오류가 난다.

각 테스트 전에 전역 엔진을 리셋해, 매 테스트가 자기 루프에서 엔진을 만들고 정리하도록 한다.
(운영 코드/아키텍처 변경 아님 — 테스트 인프라 전용.)
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from infrastructure.postgres import connection as pg


@pytest.fixture(autouse=True)
def _reset_pg_engine() -> Iterator[None]:
    pg._engine = None
    pg._session_factory = None
    yield
    pg._engine = None
    pg._session_factory = None
