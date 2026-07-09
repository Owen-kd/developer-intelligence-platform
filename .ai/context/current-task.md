# Current Task

> AI가 세션 시작 시 "지금 무엇을 하는 중인가"를 파악하는 파일. 작업이 바뀌면 갱신한다.

## 현재 스프린트
**완주 완료** — Sprint-02~13(Phase 1~4) 전 파이프라인 구현·검증 완료 (2026-07-07).
수집→그래프→Knowledge→Context→Triage/Impact Agent→Report API→Incident Library 가 end-to-end 로 동작한다.
품질 게이트 통과(ruff / mypy strict 170 files / pytest 39) + 라이브 Postgres 스모크 통과.
상세 현황: [../state/current-architecture.md](../state/current-architecture.md) · 리뷰: [../reviews/review-001.md](../reviews/review-001.md).
이전: [Sprint-01](../tasks/Sprint-01.md) 골격, Sprint 0 문서 정비 완료.

## 진행 중 (Sprint 0)
- [x] `.ai` 확장: contracts / philosophy / glossary / standards / planning / state / onboarding / references
- [x] roadmap 을 `context/` → `planning/` 으로 이동, 참조 갱신
- [x] architecture 강화: context-engine / knowledge-lifecycle
- [x] prompts 디렉터리 추가: `prompts/knowledge`, `prompts/incident`
- [x] `.ai/README.md` 인덱스 개정

## 다음 작업 (코드 재개 시 여기부터)
**[Sprint-14](../tasks/Sprint-14.md) 진행 중** — 실 어댑터 연동(LLM/Jira/Git) + Postgres 배선.
- [x] ① 실 Anthropic 어댑터([ADR-006](../decisions/ADR-006-anthropic-adapter.md)) + Postgres 배선([`apps/composition_pg`](../../apps/composition_pg.py)) — **라이브 검증 완료**(실 `claude-sonnet-5`, Postgres 영속). 승인 [APR-003](../planning/approvals/APR-003-dependencies.md)/[APR-005](../planning/approvals/APR-005-llm-vendor-data.md) 소유자 승인.
  - 부수 수정: `greenlet` 의존성 명시, `validation.py` 코드펜스 관용 파싱.
- [x] ② 실 Jira 수집 **실제 동작 확인** — `.env` 설정됨(HttpJiraClient) → DB에 **실 이슈 5000건(PA20 3000+ENG 2000) + 코멘트 29,002건 + 수집이벤트(IssueCreated 5000)** 적재됨. ⚠️ 단 [APR-002](../planning/approvals/APR-002-jira-access-pii.md) 거버넌스 승인은 여전히 Pending(공식 게이트).
- [x] ③ 실 Git 수집 동작 확인 — 커밋 6,054건 + 이슈↔커밋 링크 631건.
- [ ] 미완(자동화): **주기 스케줄러**(지금은 수동 트리거) · API를 Postgres 조회로 배선 · 이벤트 기반 자동 지식화. → 24시간 상시 서비스는 [target-service](../planning/target-service.md) 참조.
> 정정(2026-07-08): 이전 문구 "수집원은 아직 Fake"는 **런타임 실제 상태와 모순된 낡은 서술**이었음. Fake는 미설정 시 폴백일 뿐, 현 환경은 실 수집됨(위 증거). 남은 건 "가짜냐"가 아니라 "자동 주기화·거버넌스 승인".

## 지식 위키 RAG (Sprint-07 착수, 오너 지시 2026-07-08)
**목표**: 이슈 → LLM 위키 → 로컬 임베딩 → pgvector → RAG 유사검색. 사용자 비전 덱 "AI DevOps Platform"의 첫 조각.
- [x] 기반 배선 완료 — [ADR-009](../decisions/ADR-009-local-embedding-pgvector.md)(fastembed 로컬임베딩 + pgvector), [APR-004](../planning/approvals/APR-004-vector-store.md) pgvector 승인.
  - `infrastructure/embedding/`(Embedder 포트 + FastEmbed/Fake), `009_embeddings.sql`(knowledge.embedding vector(1024) + HNSW),
    `modules/knowledge/application/wiki_service.py`(+`prompts/knowledge/wiki.md`, `ask.md`), `apps/wiki_pipeline.py` + `apps/cli/wiki.py`.
  - 검증: ruff/mypy strict(193)/pytest(64) 통과 + **라이브 pgvector 스모크 통과**(build→embed→cosine top-k, 최상위=PA20-19864).
  - docker: postgres 이미지 → `pgvector/pgvector:pg16`(명명 볼륨 유지, 5000건 보존). `fastembed` 의존성 추가.
- [x] MCP 의미검색 배선 — `apps/mcp/server.py` 에 `search_wiki`(벡터 RAG) 도구 추가(+`queries.search_wiki_by_vector`). 로컬 e5 지연로딩. **라이브 확인**(질의 "쿠팡 옵션 수정 안돼요"→PA20-19875 0.83).
  - 파일럿에서 버그 수정: 위키 LLM `max_tokens` 4096(잘림 방지), `build_wikis` 이슈별 실패 격리(배치 중단 방지), mypy numpy 스텁 skip override.
- [x] 상품 도메인 위키 30건 sonnet 실 생성·임베딩 완료(실패 0). **RAG 라이브 검증**: "쿠팡 옵션 수정 안됨" → PA20-19864 0.90 최상위. 품질 양호(근본원인 정직 표기).
  - fastembed `xet` 캐시 권한 크래시 → `HF_HUB_DISABLE_XET=1` 을 embedding 어댑터에서 기본 설정(방어).
- [x] **24시간 4루프 backbone 배선 완료** → [target-service](../planning/target-service.md).
  - 루프2 자동화: `WikiAutoGenerator`(IssueCreated→자동 위키·임베딩). 루프3-Pull: `POST /ask`([apps/api/routers/ask.py](../../apps/api/routers/ask.py)) + gap 로그(`query_gaps`, 010). 루프3-Push: `RelatedKnowledgePush`(유사 위키 내부 연결, `issue_related_wiki` 011, 라이브 검증 PA20-19864→3건). 
  - 브로커: `RedisEventBus`([ADR-011](../decisions/ADR-011-redis-event-bus.md), Streams+group). 상시 진입점 `apps/worker/run` · `apps/scheduler/run`(기본 OFF, APR-002 게이트).
  - e2e 라이브: 발행→실 Redis→소비→루프2 생성 검증. 게이트 그린(ruff/mypy 201/pytest 72).
  - 미완(게이트): 실 자동수집 활성화(APR-002), Push 실 Jira 코멘트 쓰기 승인, 되먹임(gap) 활용.
- [x] **되먹임 루프** — `gap_analysis.aggregate_gaps`(유사질문 집계, 빈도+낮은커버리지 랭킹) + `gap_candidates`(gap과 겹치나 위키 없는 이슈=생성대상). CLI `wiki gaps` + API `/ask/gaps`(집계). 라이브: "쿠팡 옵션 엑셀 오류"→후보 ENG-8404. 유닛 3건. (후보매칭 키워드 기반, 의미검색 정밀화는 후속)
- [x] **정제 계층**(LLM 0, 비파괴) — `modules/knowledge/application/refinement.py`(노이즈 필터 `filter_comments` + 가치 게이트 `is_wiki_worthy`/`assess`), 노이즈목록 `config/refinement/noise_phrases.txt`(운영 조정). 위키 프롬프트는 clean 코멘트만, 신호 빈약 이슈는 인덱스만(LLM 스킵). 실측(상품 60건): 인덱스만 4 · 코멘트 드롭 7%. 원본 보존(헌법). 유닛 8건. 큰 이득은 ENG 지원도메인.
- [ ] 나머지 375건(상품 도메인 총 405건) + 타 도메인 생성 대기. `ANTHROPIC_MODEL=claude-sonnet-5 python -m apps.cli.wiki build`.
- [ ] 후속: 백엔드 도메인 지식(`gmp.openapi.2023/.ai/domains/product/`) → DIP `knowledge/` 흡수로 근본원인 grounding 강화 · 전문가 검증 루프(verified 승격) · 전량 자동수집(스케줄러, APR-002) · 접근제어([ADR-010]/[APR-010]).

## 다른 기계에서 이어가기 (Resume anywhere)
1. `git clone <origin>` → 브랜치 `feature/dip-full-build` 체크아웃.
2. Claude Code 열기 → `CLAUDE.md` 가 `.ai/` 자동 로드 → 이 파일(current-task) + [state](../state/current-architecture.md) 로 현황 파악.
3. 로컬 세팅: Python 3.11+ 설치 → `python -m venv .venv` → `.venv` 활성화 → `pip install -e ".[dev]"` → `ruff/mypy/pytest` 로 검증. (라이브 DB 검증 시 비ASCII 홈경로면 `PGSSLMODE=disable`.)
4. [Sprint-14](../tasks/Sprint-14.md) 부터 이어서 진행.
> 대화 맥락은 이 저장소의 `.ai/` 가 Single Source of Truth 다(채팅 기억은 기계 간 이동 안 됨).

## 다음 후보 (M1 — First Collector, 코드 재개 시)
- [ ] EventBus 인터페이스 (`platform/event`) → [Sprint-02](../tasks/Sprint-02.md)
- [ ] 첫 도메인 모듈: `jira` (Collector → Event → 저장) → [Sprint-03](../tasks/Sprint-03.md)
- [ ] Jira 동기화 스케줄러 (`apps/scheduler/jira_sync.py`) → Sprint-03
- [ ] Context Builder (`platform/context`) → [Sprint-06](../tasks/Sprint-06.md)
- 상세: [../planning/milestones.md](../planning/milestones.md) · [../planning/backlog.md](../planning/backlog.md)

## 완주 계획 (Project Planner 산출, 2026-07-07)
- 전체 Sprint 지도 + 의존성 그래프 + Approval Gate: **[../planning/sprint-plan.md](../planning/sprint-plan.md)**
- 사람 승인 대기(착수 전 필요): **[../planning/approvals/](../planning/approvals/)** — APR-001~009, 모두 Pending.
- 크리티컬 패스: Sprint-02 → 03 → 05 → 06 → 08 → 09 → 10 → 11 → 13.
- 주의: 코드 착수는 여전히 "현재 Sprint만". 계획 문서는 미래 구현 승인이 아니다.

## 제안된 결정 (승인 대기)
- ADR-004(제안): "AI는 Knowledge만 소비한다"를 불변 규칙으로 승격 — [APR-001](../planning/approvals/APR-001-adr004-knowledge-only.md) · [../architecture/knowledge-lifecycle.md](../architecture/knowledge-lifecycle.md) 하단 참조.
- [ADR-010](../decisions/ADR-010-team-shelf-access-control.md)(제안): 팀별 서가(component) 열람 권한·접근제어 — 기본 deny + 단일 시행계층 + 감사. 승인 [APR-010](../planning/approvals/APR-010-access-control.md) 대기. 보안 크리티컬(내부정보 유출·격리 대비).

## 메모
- 로컬 Python은 시스템 3.9 → 3.11+ 필요. venv는 Homebrew python3.14로 생성됨.
