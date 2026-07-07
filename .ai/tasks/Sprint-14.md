# Sprint-14 — 실 어댑터 연동 (LLM / Jira / Git) + Postgres 배선

- 상태: Todo
- Phase / Milestone: 실사용 전환 (walking skeleton → 첫 실데이터 동작)
- 의존성: Sprint-02~13 완료(전 파이프라인 fake/in-memory 동작)
- 선행 승인: [APR-002](../planning/approvals/APR-002-jira-access-pii.md), [APR-003](../planning/approvals/APR-003-dependencies.md), [APR-005](../planning/approvals/APR-005-llm-vendor-data.md)

## 문제 (Discovery)
현재 v0.0.1 은 **걷는 뼈대**다: 전 구간이 동작하지만 외부 연결부(LLM/Jira/Git)는 fake 어댑터이고,
실행 경로가 **in-memory**라 재시작 시 데이터가 소멸한다. "실제 데이터로 실제 판단하고 영속화"하는 첫 버전으로 전환한다.

## 범위 (포트 뒤 어댑터 교체 — 비즈니스/플랫폼 코드 불변)
- 하는 것:
  1. **실 LLM** — `infrastructure/anthropic/client.py` 에 `AnthropicClient(LLMClient)`. `.env` `ANTHROPIC_API_KEY`.
     - 값어치 1순위: 가짜 분류/영향도 → 진짜 추론. [APR-005] 데이터/비용 정책 준수, 출력 검증 유지.
  2. **실 Jira** — `infrastructure/jira/client.py` 에 `HttpJiraClient(JiraClient)` (httpx, `JIRA_*`). 읽기 전용.
  3. **실 Git** — `infrastructure/git/client.py` 에 `LocalGitClient(GitClient)` (`git log` 파싱) 또는 provider API.
  4. **Postgres 배선** — 실행 조립 루트(예: `apps/composition_pg.py`)를 `Postgres*Repository` + `PostgresEventStore` 로 구성.
     - `docker compose up` → `python -m apps.cli.migrate` → 스케줄러 적재 → API 는 DB 조회.
- 안 하는 것(Non-goals): Neo4j 실구현(별도), 실 임베딩 모델(별도), 배포/CI(별도).

## 진행 (2026-07-07)
- [x] Step 0: 승인 게이트 기록 — [APR-003](../planning/approvals/APR-003-dependencies.md)(deps) · [APR-005](../planning/approvals/APR-005-llm-vendor-data.md)(LLM) 소유자 승인.
- [x] Step 1①-a/b/d: `anthropic` 의존성([ADR-006](../decisions/ADR-006-anthropic-adapter.md)) + `infrastructure/anthropic/client.py`(`AnthropicClient(LLMClient)`) + 목킹 단위테스트. 전체 게이트 통과(ruff/mypy strict 173/pytest 41). 테스트 격리 버그(전역 async 엔진) `tests/conftest.py`로 수정.
- [x] Step 1①-c: Postgres 배선 조립 루트 [`apps/composition_pg.py`](../../apps/composition_pg.py)(`build_and_run_pg`) + 실 LLM 팩토리(`ANTHROPIC_API_KEY` 있으면 실 Anthropic, 없으면 Fake) + 러너 [`apps/cli/demo_pg.py`](../../apps/cli/demo_pg.py). 오프라인 팩토리 테스트 포함. 게이트: ruff/mypy strict 176/pytest 43.
- [x] 라이브 스모크(2026-07-07): `docker compose up` → `migrate`(001~003) → `demo_pg`.
  - Postgres 영속 확인: issues/comments/commits/events/knowledge 적재 후 독립 psql 쿼리로 검증(재시작 무관 지속).
  - 실 LLM: **`claude-sonnet-5`**(소유자 지정, opus 아님). 첫 호출 시 코드펜스(```json```)로 폴백 발생 → `dip_platform/workflow/validation.py` 관용 파싱(펜스/프로즈 추출)으로 수정 → 재실행 시 폴백 없이 Triage(확신도 0.90)·Impact 생성·검증 통과.
  - 런타임 의존성 `greenlet` 누락(신규 Python) 발견 → `pyproject.toml` 명시 추가(SQLAlchemy async 필수).

## 남은 것 (후속)
- Step 1②/③: 실 Jira([APR-002]) / 실 Git 어댑터 — 현재 수집원은 Fake.
- API 가 Postgres 에서 조회하도록 배선(`apps/api/main.py` 는 아직 인메모리 `build_and_run`). 영속 계층은 검증됨.

## 성공 기준 (DoD)
- [ ] 실 Anthropic 호출로 Triage/Impact 결과가 생성되고 스키마 검증을 통과한다(실패 시 폴백 유지).
- [ ] 실 Jira 1개 프로젝트에서 이슈/코멘트가 수집되어 Postgres 에 적재된다(멱등).
- [ ] 실 Git 저장소 커밋이 이슈에 링크된다.
- [ ] API 를 재시작해도 데이터가 유지된다(Postgres 영속).
- [ ] ruff / mypy(strict) / pytest 통과 + 라이브 연동 스모크.

## 설계 메모
- 모든 실 어댑터는 기존 포트(`LLMClient`/`JiraClient`/`GitClient`, `IssueRepository` 등)를 그대로 만족 → 상위 코드 변경 0.
- 시크릿은 `.env`(gitignore), `.env.example` 만 커밋. 운영은 시크릿 매니저.
- 신규 의존성(`anthropic`/`httpx` 런타임)은 [APR-003] 승인 후 `pyproject.toml` 에 하한 명시 + ADR.

## Approval Gate — 착수 전
- [APR-005] LLM 벤더·외부 전송 데이터 정책 / [APR-002] Jira 자격증명·PII / [APR-003] 의존성.

## 권장 순서 (최소 경로)
1. 실 Anthropic 어댑터 + Postgres 배선 → "실 LLM이 DB에 지식 축적" 확인
2. 실 Jira 수집 연동
3. 실 Git 링크 연동

## 회고
- 잘된 것:
- 개선할 것:
