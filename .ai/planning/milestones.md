# Milestones

> Roadmap Phase를 검증 가능한 이정표로 분해한다. 각 이정표는 명확한 완료 조건(DoD)을 가진다.
> 상위 방향: [roadmap.md](roadmap.md) · 대기 작업: [backlog.md](backlog.md)

## M0 — Foundation (Phase 0)
- [x] 저장소 골격 + `.ai` 헌법/워크플로우
- [x] docker-compose(postgres/neo4j/redis)
- [x] FastAPI `/health` + Postgres 연결
- [x] 품질 게이트(ruff/mypy/pytest) 동작
- [ ] `.ai` AI Operating System 확장(contracts/philosophy/standards/…)  ← Sprint 0
- **DoD:** 새 AI가 `.ai`만 읽고 프로젝트 규칙·구조·용어를 이해할 수 있다.

## M1 — First Collector (Phase 1)
- [ ] `platform/event` EventBus 인터페이스 + in-memory 구현
- [ ] `modules/jira` 도메인/서비스 골격
- [ ] `infrastructure/jira` 읽기 전용 클라이언트
- [ ] `apps/scheduler/jira_sync` 주기 수집 → Event
- [ ] `database/migrations/001_init.sql`(issues, comments, events)
- **DoD:** 이슈 1건이 Event/Timeline으로 DB에 적재된다.

## M2 — Knowledge & Context (Phase 2)
- [ ] Event/Timeline → Knowledge 승격 파이프라인
- [ ] `platform/context` Context Builder(Knowledge 기반)
- [ ] 임베딩/검색 최소 경로
- **DoD:** 이슈 1건으로 관련 Knowledge를 조회·조립할 수 있다.

## M3 — First Agent (Phase 3)
- [ ] Triage Agent(분류) — Context→LLM→검증→Event
- [ ] Impact 플레이북 자동 실행
- **DoD:** 새 이슈에 대해 자동 분류 결과가 Knowledge로 축적된다.

## 규칙
- 이정표는 "구현했다"가 아니라 "검증했다"로 완료 처리한다.
- 완료 시 [../state/current-architecture.md](../state/current-architecture.md) 를 갱신한다.
