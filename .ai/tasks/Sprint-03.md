# Sprint-03 — Jira Collector

- 상태: Todo
- Phase / Milestone: Phase 1 (Ingestion) / M1
- 의존성: **Sprint-02** (EventBus, `issues`/`comments`/`events` 테이블)
- 다음: Sprint-04 (Git Collector)

## 문제 (Discovery)
Jira 이슈/코멘트를 주기적으로 수집해 **Event → Postgres**로 적재한다. 이것이 M1의 핵심 DoD("이슈 1건이 Event/Timeline으로 DB에 적재")다.

## 범위
- 하는 것:
  - `infrastructure/jira/client.py`: **읽기 전용** Jira 클라이언트(외부 호출 격리).
  - `modules/jira`: `domain/entity.py`(`Issue`), `domain/repository.py`(추상), `infrastructure/repository.py`(Postgres 구현), `application/service.py`(`JiraService`).
  - 수집 유스케이스: 이슈/코멘트 fetch → 저장 → `IssueCreated`/`CommentAdded` 발행.
  - `apps/scheduler/jira_sync.py`: 주기 동기화(멱등 upsert).
- 안 하는 것(Non-goals):
  - Jira **쓰기**(코멘트 작성 등), 웹훅 실시간 수집(주기 폴링만), Knowledge 승격(→ Sprint-05).

## 성공 기준 (DoD)
- [ ] Jira 이슈 1건 동기화 시 `issues`/`comments` 적재 + `IssueCreated`/`CommentAdded`가 `events`에 남는다.
- [ ] 재실행해도 중복이 생기지 않는다(멱등 upsert).
- [ ] Jira/네트워크 실패 시 스케줄러가 죽지 않고 로깅 후 계속한다.
- [ ] unit 테스트에서 Jira는 **목킹**([../standards/testing.md]). ruff/mypy/pytest 통과.

## 설계 메모 (Design)
- 외부 호출은 `infrastructure/jira` 에만. `modules/jira`는 인터페이스(포트)에 의존([../contracts/module-contract.md]).
- 모듈 협업은 Event로만 — comment/git 모듈이 `IssueCreated`를 구독(직접 import 금지)([../architecture/event-flow.md]).
- 참조: [../references/jira-api.md], [../playbooks/jira-analysis.md].

## Approval Gate — 착수 전 필요
- **[APR-002]** Jira 접근·자격증명·PII 정책 (Pending).
- **[APR-003]** 신규 의존성(Jira/atlassian 클라이언트) 승인 → ADR (Pending).

## 체크리스트
- [ ] 구현 (infra client → domain → repo → service → scheduler)
- [ ] 테스트(목킹/멱등/실패격리)
- [ ] 리뷰
- [ ] 문서/`current-task` 갱신

## 회고
- 잘된 것:
- 개선할 것:
