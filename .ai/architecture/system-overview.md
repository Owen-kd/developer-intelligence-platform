# System Overview

## 레이어
```
┌─────────────────────────────────────────────┐
│ apps/     api · worker · scheduler · cli      │  실행 진입점
├─────────────────────────────────────────────┤
│ modules/  jira comment incident git code ...  │  비즈니스 (DDD-lite)
├─────────────────────────────────────────────┤
│ platform/ event workflow registry context ...│  플랫폼 코어
├─────────────────────────────────────────────┤
│ infrastructure/ jira git openai neo4j pg ...  │  외부 연동(어댑터)
├─────────────────────────────────────────────┤
│ shared/   config logger exceptions models ... │  공통
└─────────────────────────────────────────────┘
        의존성은 위 → 아래 한 방향
```

## 런타임 구성
- **API (FastAPI)**: 동기 요청 처리, 리포트 조회, 트리거.
- **Worker**: 임베딩/그래프 구축/에이전트 실행 등 무거운 비동기 작업.
- **Scheduler**: Jira/Git/Comment 주기 동기화.
- **CLI**: 운영·마이그레이션·일회성 작업.

이들은 같은 코드베이스(modules/platform)를 공유하고, 진입점만 다르다 → Modular Monolith.

## 데이터 스토어
- **Postgres**: 정형 데이터(이슈, 코멘트, 리포트).
- **Neo4j**: 관계형 그래프(코드↔이슈↔의존성).
- **Redis**: 캐시 / 이벤트·작업 브로커 후보.

## 핵심 파이프라인
```
수집(scheduler/worker) → 저장(pg/neo4j) → Context 조립(platform/context)
   → Agent 실행(platform/workflow) → 리포트(api)
```

세부: [event-flow.md](event-flow.md) · [agent-flow.md](agent-flow.md) · [database-design.md](database-design.md)
