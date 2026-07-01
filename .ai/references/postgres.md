# Reference — PostgreSQL

> DIP에서 Postgres를 어떻게 쓰는지에 대한 간략 참고. 설계: [../architecture/database-design.md](../architecture/database-design.md)

## 프로젝트 내 사용
- 역할: **정형/트랜잭션 데이터의 진실의 원천(source of truth)** — 이슈/코멘트/리포트/Event.
- 버전: `postgres:16-alpine` (docker-compose).
- 접근: SQLAlchemy 2.0 **async** + `asyncpg` 드라이버.
- 연결 코드: `infrastructure/postgres/connection.py` (engine/session/ping/dispose).

## 연결 (현재 구현)
- DSN 조립: `shared/config/settings.py` 의 `postgres_dsn`
  → `postgresql+asyncpg://user:pass@host:port/db`
- 세션: `get_session()` (FastAPI dependency), 헬스: `ping()` (실패 시 False).

## 로컬 기동
```bash
docker compose up -d postgres
# 기본값: localhost:5432 / user=dip / db=dip  (.env.example 참조)
```

## 규약 (프로젝트)
- 접근은 **infrastructure 계층**을 통해서만(모듈이 직접 드라이버 호출 금지).
- 스키마 변경은 `database/migrations/NNN_*.sql` 로만. 앱이 임의 DDL 금지.
- 테이블 복수형 `snake_case`, PK `id`, FK `<단수>_id`, 시간은 `timestamptz`(UTC), 반정형은 `jsonb`.

## 현재 상태
- 연결/헬스만 구현. **애플리케이션 테이블·마이그레이션은 아직 없음**([../state/current-architecture.md]).

## 외부 문서
- Postgres 16: https://www.postgresql.org/docs/16/
- SQLAlchemy 2.0 async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
