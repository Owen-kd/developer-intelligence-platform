# Roadmap

> 방향을 담는다. 날짜보다 순서와 목표가 중요하다.
> 세부 이정표는 [milestones.md](milestones.md), 대기 작업은 [backlog.md](backlog.md).

## Phase 0 — Foundation (현재)
- 저장소 골격 / 도구 체계 / `.ai` AI Operating System
- 실행 가능한 API + 인프라(compose)
- **Exit:** `docker compose up` + `/health` = ok, 테스트 통과.

## Phase 1 — Ingestion (Collector & Event)
- Jira 이슈/코멘트 수집(Collector) → Event → Postgres 저장
- Git 히스토리 수집
- 스케줄러 기반 주기 동기화
- **Exit:** 하나의 이슈에 대해 Jira+Comment+Git 원천 데이터가 Event/Timeline으로 적재됨.

## Phase 2 — Knowledge & Context
- Event/Timeline → **Knowledge** 승격(Promotion)
- `platform/context` Context Builder: Knowledge 기반 Context 조립
- Neo4j 그래프 + 임베딩/검색(`modules/embedding`, `modules/search`)
- **Exit:** 이슈 하나로 관련 Knowledge를 검색·조립 가능.

## Phase 3 — Agents
- EventBus 기반 Agent 오케스트레이션(`platform/workflow`)
- Triage / Impact / Review 플레이북 자동 실행
- **Exit:** 새 이슈 → 자동 분류 + 영향도 초안(결과는 Knowledge로 축적).

## Phase 4 — Product & Ops
- 리포트 UI/API, 권한(`platform/auth`), 감사(`platform/audit`)
- Incident Library 성숙, 필요 모듈의 서비스 분리 검토(Modular Monolith → 선택적 MSA)

## 분리 판단 기준
트래픽/배포주기/팀경계가 갈라지는 모듈부터 서비스로 분리한다. 그 전까지는 모노리스 유지.

## 관련
- 지식 생명주기: [../architecture/knowledge-lifecycle.md](../architecture/knowledge-lifecycle.md)
- 현재 상태: [../state/current-architecture.md](../state/current-architecture.md)
