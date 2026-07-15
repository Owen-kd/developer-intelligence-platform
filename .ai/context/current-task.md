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
- [x] MCP 의미검색 배선 — `apps/mcp/server.py` 에 `search_wiki` 도구. 로컬 e5 지연로딩. **라이브 확인**(질의 "쿠팡 옵션 수정 안돼요"→PA20-19875 0.83).
- [x] **하이브리드 검색**(BM25 FTS + 벡터, RRF 융합) — `012_knowledge_fts.sql`(tsv 생성컬럼+GIN), `repository.search_keyword`, `fusion.py`(RRF+hybrid_merge 순수), `/ask`·MCP `search_wiki` 배선. 라이브 A/B: "option_code vendorItemId" 질의에서 벡터단독은 PA20-19864 누락 → 하이브리드 #1. 순수 의미 질의는 회귀 없음. 유닛 5건.
  - 파일럿에서 버그 수정: 위키 LLM `max_tokens` 4096(잘림 방지), `build_wikis` 이슈별 실패 격리(배치 중단 방지), mypy numpy 스텁 skip override.
- [x] **리랭커**(cross-encoder 2단계 재정렬, [ADR-013](../decisions/ADR-013-cross-encoder-reranker.md), 기본 ON) — `infrastructure/embedding/reranker.py`(Reranker 포트 + FastEmbed jina-v2-multilingual/Fake, 로컬·비용0·지연로딩), `wiki_pipeline.hybrid_search`/`apply_rerank`, MCP `search_wiki` 배선. 융합 상위 `rerank_pool`(20) → 재정렬 → top-k. gap 판정은 벡터 코사인 유지. 유닛 4건. **라이브 A/B**: 정밀 질의("option_code vendorItemId")는 top-1 분리 대폭 개선(0.847≈동점 → 0.109 vs −1.096). 절충: 콜로퀴얼("옵션 수정 안돼요")은 PA20-19864 #1→#3(정답 top-3 유지, 방어가능하나 순위변동). `rerank_enabled=False` 로 즉시 롤백 가능.
- [x] **Obsidian export**(비파괴 파생 뷰, 오너 지시 2026-07-10) — `modules/knowledge/presentation/obsidian.py`(순수 `to_markdown`/`index_markdown`/`vault_filename`) + `repository.list_wikis_with_meta`/`related_wiki_keys_by_issue` + `apps/obsidian_export.py` + CLI `apps/cli/obsidian.py`. 위키→`<JIRA-KEY>.md`(YAML frontmatter: trust/서가 태그·aliases) + 관련 이슈 `[[위키링크]]`(issue_related_wiki + body.related_issues) + 서가별 `index.md` MOC. Postgres=진실원천, 볼트=편집가능 뷰(`vault/` gitignore). 라이브: 59건 export(건너뜀 0). 유닛 5건. **관찰**: 위키 `content` 필드가 구조화 필드를 중복(생성기 산물) — 후속 dedupe 여지. 다음: 편집→verified 승격 되먹임.
- [x] **검색 다양화**(MMR, [ADR-014](../decisions/ADR-014-mmr-search-diversification.md), 기본 ON, 비파괴) — `modules/knowledge/application/diversify.py::mmr_select`(순수) + `repository.embeddings_for`. 파이프라인 retrieve→(리랭커)→MMR top-k. **핵심 발견**: 같은 도메인 위키는 절대 코사인이 0.90~0.92로 몰려(스프레드 ~0.03) 절대값 페널티 무효 → 풀 안 **min-max 정규화**로 상대 다양성 복원(관련도는 랭크, 다양성은 정규화, 대칭). 설정 `diversify_enabled`/`diversify_lambda`(0.7). 유닛 6건. 라이브: "옵션 수정 안돼요" top-5 도배 → top-1 보존 + tail 이 추천옵션 정책·GTIN 등 다른 사안으로 확장. 정규화(canonicalization)는 진짜 중복 드물어(측정) 파괴적 병합 대신 이 비파괴 다양화 채택(오너 결정).
- [x] 상품 도메인 위키 30건 sonnet 실 생성·임베딩 완료(실패 0). **RAG 라이브 검증**: "쿠팡 옵션 수정 안됨" → PA20-19864 0.90 최상위. 품질 양호(근본원인 정직 표기).
  - fastembed `xet` 캐시 권한 크래시 → `HF_HUB_DISABLE_XET=1` 을 embedding 어댑터에서 기본 설정(방어).
- [x] **24시간 4루프 backbone 배선 완료** → [target-service](../planning/target-service.md).
  - 루프2 자동화: `WikiAutoGenerator`(IssueCreated→자동 위키·임베딩). 루프3-Pull: `POST /ask`([apps/api/routers/ask.py](../../apps/api/routers/ask.py)) + gap 로그(`query_gaps`, 010). 루프3-Push: `RelatedKnowledgePush`(유사 위키 내부 연결, `issue_related_wiki` 011, 라이브 검증 PA20-19864→3건). 
  - 브로커: `RedisEventBus`([ADR-011](../decisions/ADR-011-redis-event-bus.md), Streams+group). 상시 진입점 `apps/worker/run` · `apps/scheduler/run`(기본 OFF, APR-002 게이트).
  - e2e 라이브: 발행→실 Redis→소비→루프2 생성 검증. 게이트 그린(ruff/mypy 201/pytest 72).
  - 미완(게이트): 실 자동수집 활성화(APR-002), Push 실 Jira 코멘트 쓰기 승인, 되먹임(gap) 활용.
- [x] **24h 서비스 구동 배선** — `Dockerfile`(editable, 자산경로 보존) + compose 앱 서비스(api/worker/scheduler, 서비스명 호스트·hf_cache 볼륨) + 가이드 [run-24h-service](../onboarding/run-24h-service.md). **이미지 빌드+컨테이너 임포트/자산로드 검증 통과.**
- [x] **접근제어 stage1**(팀별 서가, [ADR-010](../decisions/ADR-010-team-shelf-access-control.md), 기본 OFF) — `dip_platform/access`(정책, 기본 deny) + `config/access/team_shelves.txt` + `search_semantic` 서가필터 + `/ask`(헤더 X-DIP-Team)·MCP(env DIP_TEAM) 시행 + 감사. 라이브 격리 검증(infra/support→commerce 위키 0건). 켜는 건 APR-010 승인 게이트. 유닛 3건.
- [x] **되먹임 루프** — `gap_analysis.aggregate_gaps`(유사질문 집계, 빈도+낮은커버리지 랭킹) + `gap_candidates`(gap과 겹치나 위키 없는 이슈=생성대상). CLI `wiki gaps` + API `/ask/gaps`(집계). 라이브: "쿠팡 옵션 엑셀 오류"→후보 ENG-8404. 유닛 3건. (후보매칭 키워드 기반, 의미검색 정밀화는 후속)
- [x] **정제 계층**(LLM 0, 비파괴) — `modules/knowledge/application/refinement.py`(노이즈 필터 `filter_comments` + 가치 게이트 `is_wiki_worthy`/`assess`), 노이즈목록 `config/refinement/noise_phrases.txt`(운영 조정). 위키 프롬프트는 clean 코멘트만, 신호 빈약 이슈는 인덱스만(LLM 스킵). 실측(상품 60건): 인덱스만 4 · 코멘트 드롭 7%. 원본 보존(헌법). 유닛 8건. 큰 이득은 ENG 지원도메인.
- [x] **이슈 Facet 택소노미**([ADR-015](../decisions/ADR-015-issue-faceted-taxonomy.md), 오너 승인 2026-07-10) — "이슈 저장만 말고 분류 우선". 단일 트리 대신 직교 6축(도메인·기능영역·액션·채널·유형·팀/영역). 통제 어휘는 **백엔드 실 도메인 문서**(`gmp.openapi.2023/.ai`: domain-map·glossary·domains/product)에 정렬(지어내지 않음). [taxonomy.md](../knowledge/taxonomy.md).
  - **1단계 완료(규칙 분류, LLM 0)**: `modules/knowledge/application/classification.py::classify_rule`(순수) + `013_issue_facets.sql`(issue_facets, 둘러보기 인덱스) + `jira/repository.iter_for_classification`/`save_facets` + `apps/classify_bootstrap.py` + CLI `classify bootstrap`. **라이브: 5000건 전량 분류·적재**. 규칙 커버리지: team 100%·도메인 81%·유형 78%·액션 69%·기능영역 61%(채널·영역 낮음=대부분 진짜 공통). 검증: 둘러보기 도메인>기능영역>액션 DB 작동, PA20-19864=product·option·수정·쿠팡·오류·툴·엔진. 유닛 6건.
  - **2단계 완료(LLM 보강)**: `modules/knowledge/application/classification.py`(통제어휘 `*_VOCAB` + 순수 `validate_llm_facets`, 어휘밖 무시·규칙우선) + `prompts/knowledge/classify.md`(고정어휘 JSON) + `apps/classify_enrich.py` + CLI `classify enrich`. 저가 **Haiku**(claude-haiku-4-5). 트리거는 도메인/기능영역/액션 미상만(channel=공통 제외=비용). **라이브 전량 2745건 보강(실패 0)**. 커버리지 도메인 **81→99.6%**·액션 **69→92.4%**·기능영역 63%(product 전용이라 비product는 정상적으로 미상). 미상 도메인 945→20. 유닛 2건.
  - **3단계 완료(검색 facet 필터, 비용 0)**: `repository.search_semantic`/`search_keyword` 에 `facet_filters`(축 화이트리스트 `_FACET_COLUMNS` + issue_facets EXISTS 조인, 값 파라미터화=주입방지) → `hybrid_search`/`ask`/`/ask`(domain·channel·issue_type·feature_area 필드)·MCP `search_wiki`(domain/channel/issue_type 인자) 배선. 라이브: "옵션 수정 오류"에서 channel=쿠팡은 쿠팡태그만·issue_type=오류는 기능개선 제외·domain=order는 0건. 유닛 4건.
  - **수집 배선 완료(자동 분류)**: `apps/wiki_pipeline.IssueFacetClassifier`(IssueCreated 구독 → 규칙 분류 → issue_facets 저장 → `IssueClassified` 발행, `modules/knowledge/domain/events`). 규칙만(LLM 0·즉시). `collect_and_generate`(루프1) + `apps/worker`(상시) 배선. **멱등·비파괴**: 이미 분류된 이슈는 스킵(`facets_exist`) — at-least-once 재전송이 LLM 보강을 덮지 않게. 라이브 e2e 검증(IssueCreated→classified=1→facets 갱신). 유닛 3건.
  - **기능영역 도메인 확장 완료**: 백엔드 도메인 문서(`gmp.openapi.2023/.ai/domains/{order,stock,work}/overview.md`, 별도 세션 산출)에서 기능영역 추출 → `FEATURE_BY_DOMAIN`(product/order/stock/work) + **도메인-스코프 검증**(order 기능이 product 이슈에 안 붙게) + classify 프롬프트 도메인별 목록. 라이브: order 이슈→order 기능영역 분류 확인. 유닛 1건. (기존 order/stock/work 백로그 feature_area 재보강은 선택—Haiku 소량)
  - 다음: 전문가 verified 승격 되먹임 · order/stock 백로그 위키 대량생성.
- [x] **Graphify 1단계**(Neo4j 지식 그래프, [ADR-016](../decisions/ADR-016-neo4j-graphify.md), 오너 승인 2026-07-13) — `neo4j` 드라이버 + `infrastructure/neo4j/Neo4jGraphRepository`(포트 Cypher 구현, `:Entity`+kind라벨, 라벨/관계타입 `_safe_ident` 검증=주입방지, 벌크 UNWIND) + 설정 `graph_backend`/`neo4j_*` + `apps/graph_backfill.py`(Postgres→Neo4j 멱등 MERGE) + CLI `graph backfill`. **라이브: 노드 5,884(Issue 5080·Commit 625·Component 89·Wiki 59·Channel 14·Domain 11) · 엣지 12,421 적재**. 순회 검증: PA20-19864 이웃(도메인/채널/위키/관련) + **GraphRAG 2홉**(같은 도메인+채널 이슈). Postgres=진실원천, Neo4j=파생(백필로 복원). 유닛 2건.
- [x] **Graphify 2단계(GraphRAG)**: `Neo4jGraphRepository.issue_context`(도메인/채널 + 관련위키 + **2홉 관련사안** Cypher) + MCP `graph_neighbors(jira_key)` 도구 + `GraphService` 가 `IssueClassified` 구독→이슈/도메인/채널 노드·엣지 증분(구조적 Protocol, 모듈 결합 0). node id 규약 `modules/graph/domain/model`(백필·증분 공유). 워커에 GraphService(Neo4j) 배선(graph_backend=neo4j). `IssueClassifiedPayload`에 channel 추가. 라이브: PA20-19864→관련위키 3·관련사안 8. 유닛 2건. 게이트 그린(mypy 231/pytest 133).
- [x] **위키 생성 비용 제어**(오너 지시 "매일 정오 수집→LLM 가공, 비용이 문제"; 모델 결정=Haiku) — 수집·분류·정제는 LLM 0(무료), 비용은 위키 생성(sonnet)뿐임을 실측(정제 값게이트 99% 통과=사실상 무필터). 대책 2개: (1) **유형 게이트** `_wiki_type_allowed`(facet issue_type ∈ `wiki_types`=오류/기능개선만, 문의 스킵) — WikiAutoGenerator/build_wikis/worker 배선, (2) **`wiki_model` 설정**(기본 `claude-haiku-4-5`, sonnet 대비 ~3x 저렴) `_build_wiki_llm`. 라이브: Haiku 위키 1건 생성 성공. 유닛 3건. **관찰**: product엔 문의 유형 0(문의는 inquiry-as 도메인)이라 유형게이트가 product에선 미상 373 스킵 → `미상`도 포함하려면 WIKI_TYPES 조정. 백로그 일괄은 Batch API(50%)가 추가 레버(후속).
- [x] **위키 생성 도메인 확장**(오너 지시 "주문도 만들어줘") — 컴포넌트 키워드 게이트(상품/쿠팡) → **facet 도메인 게이트**로 교체. `_domain_issue_ids`(issue_facets.domain 기반 후보) + `WikiAutoGenerator` 도메인+유형 게이트(classify_rule 1회로 둘 다) + 설정 `wiki_domains`(기본 `product,order`). build_wikis/collect_and_generate/worker 배선. 라이브: order 후보 276건, Haiku로 order 위키 생성 검증(PA20-19873 근본원인 정상). 유닛 갱신. 이제 도메인 확장은 `WIKI_DOMAINS`에 추가만(예: stock).
- [x] **지식 베이스 구축(상품+주문 백로그)** — Haiku로 대량 생성. 위키 90→**416건**(product 287·order 128, 실패 0, ~$2.3). 유형/가치 게이트로 274건은 인덱스만(비용 절감). 그래프 노드 6,248. 실사용 가능 규모 도달.
- [x] **PII 마스킹**(개인정보 제거, LLM 0·결정적·비파괴, 오너 지시 2026-07-13) — `refinement.redact_pii`(순수 함수, 정규식): 주민번호·카드·전화·이메일·사업자번호·API토큰. 경계는 `\b` 대신 숫자 lookaround(`(?<!\d)…(?!\d)`) — 한글 인접("번호는01012345678") 대응. **2중 방어**: (1)입력 `wiki_service._render_user` 프롬프트 마스킹→Anthropic이 PII 미열람, (2)출력 `_to_knowledge` 저장 전 마스킹→벡터DB·Obsidian·MCP 청정, (3)`wiki.md` 프롬프트에 이름·주소 등 자유형 PII 출력 금지 지시(정규식 밖 보완). `classify_enrich` 제목도 마스킹. **실 데이터 검증**: 코멘트 표본 376건 PII 86개→마스킹 후 0. 기존 위키 670건 백필(진짜 PII 2건 청소, 재임베딩+볼트 재export)→정밀 PII 잔존 0. 유닛 6건. **한계(정직)**: 구조화 식별자만—이름·주소는 프롬프트 지시 의존, 국제전화(+82) 미포함. 원본(Postgres)은 불변.
- [x] **검증 지식 승격**(오너 제공, 2026-07-14) — 주문 **추가 컬럼(addcol)** 기능: addcol 테이블 `wm_no` 임의값 무방 · 노출항목설정>항목추가(최대 8개, 문자/숫자) · 백오피스 `2.0 회원상세>모듈 관리>'컬럼 추가 여부(주문)'` Y/N 로 업체 접근 제어(필수 커스텀컬럼 업체는 삭제 방지 위해 미개방). `source=verified`, issue_id 없음(전문가 종합), 사진 3장 근거. 라이브 RAG 검증: "노출항목설정 항목추가"·"addcol wm_no" 질의에서 #1. 현재 verified 2건(요금과충전 PA20-19112 + addcol).
- [x] **Obsidian standalone 지원**(비파괴) — 이슈에 안 매인 verified 지식이 export에서 제외되던 것 해결. `obsidian.standalone_vault_path`(→`검증지식/<slug>-<id8>.md`) + `to_markdown` 제목이 Jira 키 없으면 요약만(uuid 미노출). export 앱이 skip 대신 기록. 라이브: 671건 전량 export(건너뜀 0), addcol 지식이 `vault/검증지식/`에 표출. 유닛 1건. **관찰**: 깨끗한 order 이슈 링크 대상 없음(addcol 이슈 PA20-17635는 product로 오분류·타 컬럼이슈는 위키 있어 충돌) → 억지 링크 대신 standalone 채택.
- [x] **Notion 지식 소화(스케줄러/배치 카탈로그)**(오너 제공, 2026-07-14) — 팀 Notion 문서(DB Scheduler 4 + CloudWatch Rules)를 **작업별 1건**으로 verified 승격(총 17건, LLM 0·이미 정제됨). admin/gmp/tmp/mts daily_scheduler · gmp_invoice_bot · setBackendProcess(checkNullOrdBundleNo·sync-count 등) · systemAutoProcess · change-ecs-task-number 등 + 폐기규칙(check-null-bundleno→setBackendProcess 통합) 별도 보존. standalone(`검증지식/`). 라이브 RAG: "개인정보 마스킹 스케줄러"→gmp.daily_scheduler #1, "check-null-bundleno 없어졌나"→폐기규칙 #1(+요금과충전 자동연결). **관찰**: setBackendProcess는 서브작업 16개 카탈로그라 단일 서브항목 순수벡터 질의는 희석("묶음번호 미생성 언제"는 버그위키가 상위) → 실사용 hybrid(BM25)가 완화. 소스 형식 무관 파이프라인 입증(Notion→knowledge).
- [x] **신세계 도메인 타깃 가공**(오너 지시 2026-07-14) — 신세계(신세계푸드) 관련 & PA20-18000+ 이슈를 도메인 무관 전부 위키화. 이미 수집돼 있어 가공만: 대상 66건 중 위키없는 48건 → **생성 47·인덱스만 1·실패 0**(커버리지 65/66). **유형 게이트 우회**(문의·미상·settings·pay 등 도메인 다양, "전부" 요청)하되 가치 게이트·PII 마스킹·grounding·임베딩은 파이프라인 그대로 재사용(타깃 스크립트, Haiku ~$0.33). 그래프 6,549노드·볼트 752건 반영. RAG: "신세계푸드 주문 오류"→새 derived #1·#2, "신세계 사은품 규칙"→verified(ord_sfood_s) #1. build_wikis 는 도메인+유형 게이트라 이런 횡단 타깃은 별도 선택(향후 CLI `--filter` 여지).
- [x] **프로덕션 대비 — RAG 평가 하네스**(회귀 가드, 오너 지시 "93% 확신 측정") — `apps/eval_rag.py`(build=Haiku로 구어체 질문 생성→골든 영속 / run=결정적·LLM 0 측정) + `tests/eval/golden_qa.jsonl`(60건 고정) + `prompts/eval/question_gen.md`. **baseline: 전체 hit@5=90%·hit@1=88%, derived(실답 위키)=95%, verified=80%**(miss는 grounding 청크·추상개념=직접답 아님). 변경 전후 `python -m apps.eval_rag`로 회귀 감시. 측정 축=검색 정확도(paraphrase); 커버리지·합성충실도는 별도.
- [x] **프로덕션 대비 — 읽기전용 DB 롤**(멀티유저 보안 게이트) — `014_readonly_role.sql`(`dip_reader`: SELECT 전체 + query_gaps INSERT만, **comments(원천 PII) 조회 REVOKE**=심층방어, 원천 변조 불가). 라이브 검증: 코멘트/삭제/수정 permission denied, 위키·이슈 조회·gap로깅 허용. `settings.postgres_reader_dsn`(미설정 시 폴백) + `.env.example`. **F 잔여(사람 게이트/후속)**: API가 reader DSN 접속 배선(배포), 감사 영속화(InMemory→DB), 접근제어 ON+정책(APR-010), 자동수집 APR-002.
- [ ] 실사용: MCP(search_wiki/graph_neighbors) Claude Desktop 연결 · 엔진(문의) 지식화는 대기(오너 결정). `ANTHROPIC_MODEL=claude-sonnet-5 python -m apps.cli.wiki build`.
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
