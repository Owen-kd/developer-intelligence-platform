# Sprint-08 — LLM 인프라 + registry + workflow (+ audit 최소)

- 상태: Todo
- Phase / Milestone: Phase 3 (Agents) / M3
- 의존성: **Sprint-06** (Context 존재)
- 다음: Sprint-09 (Triage Agent)

## 문제 (Discovery)
Agent를 실행하려면 ① 벤더 격리된 **LLM 호출 인프라**, ② **프롬프트/Agent registry**, ③ step 오케스트레이션 **workflow**, ④ 각 step 입출력을 남길 최소 **audit**이 필요하다([../architecture/agent-flow.md]).

## 범위
- 하는 것:
  - `infrastructure/openai`, `infrastructure/anthropic`: 공통 인터페이스(포트) 뒤의 LLM 호출 어댑터.
  - `platform/registry`: Agent/Prompt 등록·조회(`prompts/` 파일 로드).
  - `platform/workflow`: step 1..N 실행 골격(입력=Context+prompt → LLM → **검증**).
  - `platform/audit`(최소): step 입출력 감사 기록([APR-006]에서 조기 도입 승인).
- 안 하는 것(Non-goals):
  - 구체 Agent 로직(→ Sprint-09/10), 재시도/폴백 고도화(기본만), 권한(→ Sprint-12).

## 성공 기준 (DoD)
- [ ] 동일 인터페이스로 OpenAI/Anthropic 중 하나를 호출하고, 벤더 교체가 Agent 코드에 영향 없음(어댑터 교체만).
- [ ] registry에서 프롬프트를 **파일**로 로드(코드 인라인 0).
- [ ] workflow가 Context+prompt로 1-step을 실행하고 출력 스키마를 검증한다(실패 시 폴백 경로).
- [ ] 각 step 입출력이 audit에 남는다. unit은 LLM 목킹. ruff/mypy/pytest 통과.

## 설계 메모 (Design)
- 벤더 직접 호출 금지 → 반드시 `infrastructure` 경유([../contracts/agent-contract.md]).
- LLM 출력은 신뢰하지 않고 항상 검증([../core/coding-guidelines.md]).

## Approval Gate — 착수 전
- **[APR-005]** LLM 벤더 기본값 + **외부 전송 데이터 정책**(Context가 외부로 나감) (Pending).
- **[APR-006]** `platform/audit` 조기 도입(마일스톤 순서 이탈) (Pending).
- **[APR-003]** 의존성(openai/anthropic SDK) → ADR (Pending).

## 체크리스트
- [ ] 구현 (llm infra → registry → workflow → audit)
- [ ] 검증/폴백/목킹 테스트
- [ ] 리뷰
- [ ] `state` 갱신

## 회고
- 잘된 것:
- 개선할 것:
