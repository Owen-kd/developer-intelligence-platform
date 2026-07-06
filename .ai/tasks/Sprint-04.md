# Sprint-04 — Git Collector + 이슈↔커밋 링크

- 상태: Todo
- Phase / Milestone: Phase 1 (Ingestion) / M1
- 의존성: **Sprint-02**(EventBus), **Sprint-03**(이슈 존재 → 링크 대상)
- 다음: Sprint-05 (Knowledge 승격)

## 문제 (Discovery)
이슈 하나의 맥락을 완성하려면 Jira뿐 아니라 **Git 히스토리**(관련 커밋)가 필요하다(roadmap Phase 1).
Phase 1의 최종 Exit: "이슈 하나에 Jira+Comment+**Git** 원천이 Event/Timeline으로 적재".

## 범위
- 하는 것:
  - `database/migrations/002_commits.sql`: `commits`, `issue_commits`([../architecture/database-design.md]).
  - `infrastructure/git/client.py`: 저장소 히스토리 읽기(읽기 전용).
  - `modules/git`: 커밋 수집 → 저장 → `CommitsCollected`/`CommitsLinked` 발행.
  - 이슈↔커밋 링크: 커밋 메시지의 이슈 키(예: `PROJ-123`) 파싱으로 연결.
  - `apps/scheduler/git_sync.py`: 주기 동기화(멱등).
- 안 하는 것(Non-goals):
  - diff/코드 파싱·그래프 적재(→ Sprint-07), Git **쓰기**, PR/리뷰 수집.

## 성공 기준 (DoD)
- [ ] 커밋 동기화 시 `commits` 적재 + 메시지 내 이슈키로 `issue_commits` 링크 생성.
- [ ] `CommitsLinked` 이벤트가 `events`에 남는다.
- [ ] 재실행 멱등, 외부 실패 시 스케줄러 생존.
- [ ] Git은 unit에서 목킹. ruff/mypy/pytest 통과.

## 설계 메모 (Design)
- 외부 호출은 `infrastructure/git` 에만. `modules/git`은 인터페이스 의존.
- 링크는 이벤트 기반: `IssueCreated` 구독 또는 커밋 파싱 결과로 `CommitsLinked` 발행(모듈 직접 import 금지).
- 이 시점에 Phase 1 Exit 검증(이슈 1건 = Jira+Comment+Git).

## Approval Gate — 착수 전
- **[APR-003]** Git 접근 라이브러리(예: GitPython/네이티브) 의존성 → ADR (Pending).

## 체크리스트
- [ ] 구현 (migration → infra → module → scheduler)
- [ ] 테스트
- [ ] 리뷰 · Phase 1 Exit 확인
- [ ] `milestones`(M1) / `state` 갱신

## 회고
- 잘된 것:
- 개선할 것:
