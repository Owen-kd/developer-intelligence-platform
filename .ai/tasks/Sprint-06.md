# Sprint-06 — Context Builder

- 상태: Todo
- Phase / Milestone: Phase 2 (Knowledge & Context) / M2
- 의존성: **Sprint-05** (Knowledge 존재)
- 병렬: Sprint-07 · 다음: Sprint-08

## 문제 (Discovery)
Agent가 쓸 **Context**를 Knowledge 기반으로 일관·재현 가능하게 조립해야 한다("Context Before AI").

## 범위
- 하는 것:
  - `platform/context`: 입력 `(task, target_id)` → 관련 Knowledge 조회 → 선별/랭킹 → 토큰 예산 구성 → **출처 첨부**.
  - 출력 DTO: `Context { task, target, knowledge[], sources[], budget_meta }`.
  - **결정적 조립**(같은 입력 → 같은 Context) 보장.
- 안 하는 것(Non-goals):
  - 임베딩 기반 랭킹(→ Sprint-07 연동은 후속), 프롬프트/LLM 호출(Agent 몫), 원천 데이터 사용(금지).

## 성공 기준 (DoD)
- [ ] 이슈 1건으로 관련 Knowledge를 조회·조립한 Context가 생성된다(M2 DoD).
- [ ] Context는 **원천 데이터가 아니라 Knowledge**만 담는다([../architecture/context-engine.md]).
- [ ] 동일 입력 2회 → 동일 Context(재현성 test).
- [ ] 토큰 예산 초과 시 신호 우선 절삭. ruff/mypy/pytest 통과.

## 설계 메모 (Design)
- 배치: `platform/context`(오케스트레이션). 데이터 수집은 모듈/인프라, 조립만 여기서.
- 계약: [../contracts/agent-contract.md](입력), [../contracts/knowledge-contract.md](소비).
- 프롬프트는 Context에 섞지 않는다(Agent가 별도 로드).

## Approval Gate
- 없음(신규 외부 의존성 없음). 단 [APR-001] 확정이 전제.

## 체크리스트
- [ ] 구현 (조회 → 랭킹 → 예산 → 출처)
- [ ] 재현성/예산 테스트
- [ ] 리뷰
- [ ] `state` 갱신

## 회고
- 잘된 것:
- 개선할 것:
