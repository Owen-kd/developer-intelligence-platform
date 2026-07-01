# Current Task

> AI가 세션 시작 시 "지금 무엇을 하는 중인가"를 파악하는 파일. 작업이 바뀌면 갱신한다.

## 현재 스프린트
[Sprint-01](../tasks/Sprint-01.md) — 프로젝트 스캐폴딩 & 골격.

## 진행 중
- [x] 저장소 골격 (apps/modules/platform/infrastructure/shared)
- [x] docker-compose (postgres/neo4j/redis)
- [x] pyproject / .env.example / .gitignore
- [x] FastAPI 부트스트랩 + `/health` (Postgres ping)
- [x] `.ai/` 핵심 문서 (core / context / architecture / decisions / workflow / playbooks)
- [ ] EventBus 인터페이스 (`platform/event`)
- [ ] 첫 도메인 모듈: `jira` (수집 → 저장)

## 다음 후보
- Jira 동기화 스케줄러 (`apps/scheduler/jira_sync.py`)
- Context 조립 오케스트레이터 (`platform/context`)

## 메모
- 로컬 Python은 시스템 3.9 → 3.11+ 필요. venv는 Homebrew python3.14로 생성됨.
