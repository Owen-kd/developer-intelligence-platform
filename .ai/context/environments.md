# Environments

## local (기본)
- 실행: `docker compose up -d` + `uvicorn apps.api.main:app --reload`
- 설정: `.env` (템플릿 `.env.example`)
- Postgres `localhost:5432` / Neo4j `localhost:7687`(browser 7474) / Redis `localhost:6379`
- `APP_ENV=local`, `APP_DEBUG=true`

## test
- pytest 실행 컨텍스트. 외부 시스템은 목킹이 원칙.
- integration/e2e는 실제 compose 인프라를 대상으로 별도 실행.
- DB 접속 불가 시에도 `/health`는 200(status=degraded)을 반환하도록 설계됨.

## staging / production (예정)
- 시크릿은 환경변수/시크릿 매니저로 주입. 저장소에 넣지 않는다.
- `APP_DEBUG=false`, SQL echo off.
- 마이그레이션은 배포 파이프라인에서 `database/migrations` 순서대로 적용.

## 설정 규칙
- 모든 설정은 `shared/config/settings.py` 를 단일 소스로 통과한다.
- 코드에서 `os.environ` 을 직접 읽지 않는다.
- 새 설정 키는 `.env.example` 에도 반드시 추가한다.
