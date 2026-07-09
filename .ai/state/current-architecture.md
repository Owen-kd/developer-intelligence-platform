# State — Current Architecture

> **지금 실제로 구현된 것**만 기록한다(설계 의도가 아니라 현실). 이정표 완료 시 갱신한다.
> 목표 구조: [../architecture/](../architecture/) · 로드맵: [../planning/roadmap.md](../planning/roadmap.md)

_기준: Phase 0~4 전 구간 구현 완료 / Sprint-02~13 (전 파이프라인 동작·검증)._
_품질 게이트: ruff / mypy(strict, 170 files) / pytest 39건 통과. 라이브 Postgres 스모크 통과._

## 실제로 존재하고 동작하는 것
- **기반**
  - `dip_platform/event` — EventBus(in-memory) + append-only EventStore(in-memory/Postgres). 핸들러 격리.
    (패키지명은 stdlib 충돌로 `platform`→`dip_platform` 리네임 — [ADR-005](../decisions/ADR-005-platform-package-rename.md).)
  - `database/migrations` — `001_init`(issues/comments/events), `002_commits`, `003_knowledge`. `apps/cli/migrate` 로 적용.
  - `shared/logger`(구조화 로깅), `shared/exceptions`(도메인 예외), `shared/constants`.
- **Phase 1 — Ingestion**
  - `modules/jira` + `infrastructure/jira`(FakeJiraClient) + `apps/scheduler/jira_sync` — 이슈/코멘트 수집 → 멱등 upsert → IssueCreated/CommentAdded.
  - `modules/git` + `infrastructure/git`(FakeGitClient) + `apps/scheduler/git_sync` — 커밋 수집 + 이슈키 파싱 링크 → CommitsLinked. (git 은 IssueCreated 구독으로 매핑 학습, 모듈 직접 import 없음.)
- **Phase 2 — Knowledge & Context**
  - `modules/knowledge` — Event/Timeline → Knowledge 승격(출처 보존, append, 검증). Agent 결과도 Knowledge 로 축적.
  - `dip_platform/context` — 결정적 Context Builder(토큰 예산/출처). KnowledgeSource 포트를 knowledge 모듈이 구현.
  - `modules/graph`(in-memory) — CommitsLinked 구독으로 (:Commit)-[:FIXES]->(:Issue) 구축, 영향 커밋 탐색.
  - `modules/embedding` + `modules/search` — 결정적 로컬 임베딩 + 코사인 검색.
- **Phase 3 — Agents**
  - `infrastructure/llm`(FakeLLMClient, 벤더 중립 포트) + `dip_platform/registry`(파일 프롬프트) + `dip_platform/audit` + `dip_platform/workflow`(Agent/Runner/검증).
  - Triage Agent + Impact Agent — Context Before AI, LLM 출력 검증, 실패 시 폴백. 결과 → Event → Knowledge.
  - 프롬프트 자산: `prompts/triage/classify.md`, `prompts/impact/analyze.md`.
- **Phase 4 — Product & Ops**
  - `apps/api` — `/health` + `/issues` + `/impact-analyses` + `/incidents`(Bearer 인증 + 접근 감사).
  - `dip_platform/auth`(정적 토큰) + `dip_platform/audit`.
  - `modules/incident` — Knowledge → Incident Library 승격(근본원인, 사실 근거 필수).
  - `apps/composition`(조립 루트) + `apps/cli/demo` — 전 파이프라인 1회 실행 데모.

## 검증 방식
- 단위/통합 테스트 39건(모든 어댑터는 fake/in-memory 로 결정적). `apps/cli/demo` e2e 실행 확인.
- 라이브 Postgres: `scripts/pg_smoke.py` 로 마이그레이션 + Postgres 어댑터(멱등 upsert/이벤트 적재/조회) 검증.

## Sprint-14 진행분 (실 어댑터 전환)
- **실 Anthropic LLM** `infrastructure/anthropic`(`AnthropicClient`) — 라이브 검증 완료(`claude-sonnet-5`). [ADR-006].
- **Postgres 배선 조립 루트** `apps/composition_pg`(+`apps/cli/demo_pg`) — 전 파이프라인이 Postgres 에 영속. 라이브 스모크 통과.
- `dip_platform/workflow/validation.py` — 실 LLM 코드펜스/프로즈 출력도 관용 파싱(검증은 유지).
- `greenlet` 런타임 의존성 명시(SQLAlchemy async 필수).

## 아직 fake/로컬로만 있는 것 (실 어댑터는 승인 게이트)
- 실 Jira 연동([APR-002]), 실 OpenAI([APR-005] — Anthropic 은 완료), Neo4j 드라이버·벡터스토어([APR-003]/[APR-004]).
- `apps/api` 는 아직 인메모리 `build_and_run` 을 서빙(영속 배선은 `composition_pg` 로 검증됨, API 배선은 후속).
  모두 **같은 포트 뒤에서 교체**만 하면 되며 비즈니스/플랫폼 코드 변경 불필요.

## 알려진 이슈/후속
- `docker-compose` 는 명명 볼륨으로 전환(Windows 바인드 마운트 권한 오류 회피).
- asyncpg + 비ASCII 홈경로에서 SSL 인증서 로드 이슈 → 로컬 검증 시 `PGSSLMODE=disable` 사용.
- Postgres 어댑터 타임스탬프는 ISO 문자열→datetime 변환으로 바인딩(어댑터 경계에서 처리).
