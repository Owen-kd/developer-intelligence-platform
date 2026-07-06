# Sprint Plan — 프로젝트 완주 계획

> Project Planner(AI)가 `.ai` 전체를 읽고 자동 생성한, **프로젝트를 끝까지 개발하기 위한 Sprint 전체 계획**이다.
> 상위 방향: [roadmap.md](roadmap.md) · 이정표: [milestones.md](milestones.md) · 대기 작업: [backlog.md](backlog.md)
>
> 규칙: 이 문서는 **계획**이다. 실제 구현은 "현재 Sprint만" 한다([../core/system.md]).
> 아키텍처를 재설계하지 않는다. 사람이 결정해야 하는 지점은 **Approval Request**([approvals/](approvals/))로 분리했다.

---

## 1. 전체 Sprint 지도

| Sprint | Phase | Milestone | 목표 | 주요 배치 |
|--------|-------|-----------|------|-----------|
| [Sprint-01](../tasks/Sprint-01.md) | 0 | M0 | 실행 가능한 골격 + `.ai` OS | apps/api, shared, infra/postgres |
| [Sprint-02](../tasks/Sprint-02.md) | 1 | M1 | **EventBus + 초기 스키마** | `platform/event`, `database/migrations/001` |
| [Sprint-03](../tasks/Sprint-03.md) | 1 | M1 | **Jira Collector** | `modules/jira`, `infrastructure/jira`, `apps/scheduler/jira_sync` |
| [Sprint-04](../tasks/Sprint-04.md) | 1 | M1 | **Git Collector + 이슈↔커밋 링크** | `modules/git`, `infrastructure/git`, `apps/scheduler/git_sync` |
| [Sprint-05](../tasks/Sprint-05.md) | 2 | M2 | **Knowledge 승격 파이프라인** | `modules/incident?`→ Promotion, Timeline, Knowledge Library |
| [Sprint-06](../tasks/Sprint-06.md) | 2 | M2 | **Context Builder** | `platform/context` |
| [Sprint-07](../tasks/Sprint-07.md) | 2 | M2 | **임베딩·검색·그래프** | `modules/embedding`, `modules/search`, `modules/graph`, `infrastructure/neo4j` |
| [Sprint-08](../tasks/Sprint-08.md) | 3 | M3 | **LLM 인프라 + registry + workflow(+audit 최소)** | `infrastructure/{openai,anthropic}`, `platform/registry`, `platform/workflow`, `platform/audit` |
| [Sprint-09](../tasks/Sprint-09.md) | 3 | M3 | **Triage Agent** | `platform/workflow`, `prompts/triage` |
| [Sprint-10](../tasks/Sprint-10.md) | 3 | M3 | **Impact Agent** | `platform/workflow`, `prompts/impact` |
| [Sprint-11](../tasks/Sprint-11.md) | 4 | M4 | **Report API** | `apps/api/routers` (issues, impact-analyses) |
| [Sprint-12](../tasks/Sprint-12.md) | 4 | M4 | **Auth + Audit 완성** | `platform/auth`, `platform/audit` |
| [Sprint-13](../tasks/Sprint-13.md) | 4 | M4 | **Incident Library + 선택적 MSA 분리 검토** | Incident Library, 분리 판단 |

> M4는 roadmap Phase 4를 검증 가능한 이정표로 승격한 것(현재 milestones.md에는 M3까지만 존재 — [APR-008] 참고).

---

## 2. 의존성 그래프 (Dependency Analysis)

```
Sprint-01 (done: 골격)
    │
    ▼
Sprint-02  EventBus + migrations(001)
    │            │
    ▼            └──────────────┐
Sprint-03  Jira Collector       │
    │                           ▼
    ▼                     Sprint-04  Git Collector
    └──────────┬────────────────┘
               ▼
        Sprint-05  Knowledge 승격  (Event/Timeline → Knowledge)
               │
        ┌──────┴───────┐
        ▼              ▼
 Sprint-06         Sprint-07
 Context Builder   임베딩·검색·그래프
        │              │
        └──────┬───────┘
               ▼
        Sprint-08  LLM 인프라 + registry + workflow + audit(min)
               │
               ▼
        Sprint-09  Triage Agent
               │
               ▼
        Sprint-10  Impact Agent   ◀── (Sprint-07 그래프 필요)
               │
               ▼
        Sprint-11  Report API
               │
        ┌──────┴───────┐
        ▼              ▼
 Sprint-12         Sprint-13
 Auth + Audit      Incident Library + MSA 분리 검토
```

### 크리티컬 패스
`02 → 03 → 05 → 06 → 08 → 09 → 10 → 11 → 13`

### 병렬 가능
- **Sprint-04**(Git)는 Sprint-03 완료 후 Sprint-05와 별개로 진행 가능(단, 05는 04의 Event도 소비하면 더 풍부해짐 → 04를 05 앞에 두는 것을 권장).
- **Sprint-06**(Context)과 **Sprint-07**(임베딩/그래프)는 둘 다 Sprint-05(Knowledge)에만 의존 → **병렬**.
- **Sprint-12**와 **Sprint-13**은 Sprint-11 이후 병렬.

### 역방향 의존 점검 (아키텍처 가드레일)
모든 Sprint는 `apps → modules → platform → infrastructure → shared` 한 방향을 지킨다.
- Collector(03/04): 외부 호출은 `infrastructure/{jira,git}` 에만. 모듈은 인터페이스에 의존.
- 모듈 간 협업은 **Event**로만(직접 import 금지) — 특히 05가 03/04 산출 Event를 EventBus로 소비.
- Agent(09/10): 원천 데이터 직접 소비 금지 → 반드시 `platform/context` 경유. LLM은 `infrastructure` 경유.

---

## 3. Approval Gate (사람 결정이 막는 지점)

각 Gate는 해당 Sprint **착수 전** 승인이 필요하다. 상세: [approvals/](approvals/).

| Gate | Approval | 막는 Sprint | 왜 사람이 결정하나 |
|------|----------|-------------|--------------------|
| G1 | [APR-002](approvals/APR-002-jira-access-pii.md) — Jira 접근·자격증명·PII 정책 | Sprint-03 | 실데이터/자격증명/개인정보 취급 |
| G2 | [APR-003](approvals/APR-003-dependencies.md) — 신규 런타임 의존성 배치 | 03·07·08 | 의존성 추가는 ADR 필요([coding-guidelines]) |
| G3 | [APR-001](approvals/APR-001-adr004-knowledge-only.md) — ADR-004 "AI는 Knowledge만 소비" 승격 | Sprint-05 | 불변 규칙 확정 |
| G4 | [APR-006](approvals/APR-006-audit-early.md) — `platform/audit` 조기 도입 | Sprint-08 | 마일스톤 순서 이탈(설계 판단) |
| G5 | [APR-004](approvals/APR-004-vector-store.md) — Vector store 선택 | Sprint-07 | 데이터 아키텍처 결정 |
| G6 | [APR-005](approvals/APR-005-llm-vendor-data.md) — LLM 벤더 기본값·외부 전송 데이터 정책 | Sprint-08 | 데이터가 외부 LLM으로 나감/비용 |
| G7 | [APR-007](approvals/APR-007-eventbus-broker.md) — EventBus 브로커 전환 시점 | (스케일 시) | 운영·확장 판단 |
| G8 | [APR-008](approvals/APR-008-msa-separation.md) — MSA 분리 결정 | Sprint-13 | 조직/배포 경계 결정 |

---

## 4. 사용법
1. 다음 Sprint 착수 시: 해당 Sprint 파일을 열고 [../workflow/01-discovery.md] 부터 시작.
2. 관련 Approval Gate가 **Pending**이면 착수 전 승인부터 받는다.
3. Sprint 완료 시: [milestones.md] 체크, [../state/current-architecture.md] 갱신, [../context/current-task.md] 이동.

## 관련
- [../architecture/knowledge-lifecycle.md] · [../architecture/event-flow.md] · [../architecture/context-engine.md]
- [../contracts/](../contracts/) (event/module/knowledge/agent/api 계약)
