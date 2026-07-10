# ADR-013 — Cross-encoder 리랭커 (하이브리드 검색 2단계 재정렬)

- 상태: Accepted
- 날짜: 2026-07-10
- 관련: [ADR-009](ADR-009-local-embedding-pgvector.md)(로컬 임베딩+pgvector) · 하이브리드 검색(012_knowledge_fts, fusion.py)

## 맥락
하이브리드 검색(벡터 bi-encoder + BM25 전문검색, RRF 융합)은 1차 후보를 잘 모으지만,
**상위권 순위 변별력**은 약하다. bi-encoder 는 질의와 문서를 각각 독립 임베딩해 코사인만 보므로
질의-문서 상호작용(교차 주의)을 못 본다. 라이브에서 "option_code vendorItemId 비교 로직" 질의는
top-5 코사인이 0.847~0.858 로 사실상 동점 — 정답(PA20-19864)이 1위여도 2위와 구분이 안 됐다.

## 결정
융합 상위 소수 후보(`rerank_pool`, 기본 20)를 **로컬 cross-encoder** 로 질의-문서 쌍 채점해 재정렬한 뒤
top-k 로 자른다. bi-encoder 보다 정밀하지만 느려서 **넓게 뽑고 좁게 재정렬**하는 2단계 구조로 비용을 억제한다.

- **포트-어댑터**: `infrastructure/embedding/reranker.py` 에 `Reranker` 포트 + `FastEmbedReranker`(로컬)·`FakeReranker`(결정적, 테스트).
- **모델**: fastembed `TextCrossEncoder`, `jinaai/jina-reranker-v2-base-multilingual`(다국어, 한국어 지원). 로컬 = API 비용 0, 데이터 반출 없음(ADR-009 원칙 유지).
- **지연 로딩**: 최초 사용 시 다운로드/캐시(임베더와 동일 패턴, threading.Lock 이중검사). `get_reranker()` lru_cache 로 프로세스 단일 warm 인스턴스.
- **배선**: `apps/wiki_pipeline.hybrid_search()` + `apply_rerank()`, MCP `search_wiki`(`queries.search_wiki_hybrid` reranker 인자). 설정 `rerank_enabled`(기본 ON)·`reranker_model`·`rerank_pool`.
- **gap 판정은 벡터 커버리지 유지**: 리랭커/융합이 순위를 바꿔도 "지식 있음/없음" 신호는 의미유사도(코사인) 원본(`vector_hits`)으로 판정 — 리랭커 점수는 무한 로짓이라 임계값 부적합.

## 근거
- cross-encoder 는 질의-문서를 함께 인코딩해 교차 주의 → 상위권 변별력이 bi-encoder 보다 크게 높다(정보검색 표준 2단계 파이프라인: retrieve → rerank).
- 소수 후보(20)에만 적용 → 지연 최소. 전량 재정렬(5000+)은 불가하지만 융합이 이미 후보를 좁혀줌.
- 로컬 유지 → ADR-009 의 "임베딩/재정렬은 로컬, LLM 만 벤더" 경계 일관.

## 절충 / 리스크 (정직 보고)
- **콜로퀴얼 질의에서 순위 변동**: 라이브 "쿠팡에서 옵션이 수정이 안돼요" 는 리랭커 ON 시 PA20-19864(버그)가
  #1→#3 으로 밀리고 "수정 제한 안내문구/수정 가능 범위 제한" 문서가 상승. 언어적으로는 방어 가능("수정이 안돼요"↔"수정 제한")
  이나, 사용자가 canonical 로 여기던 답을 강등한다. 정답은 여전히 top-3 안(유실 아님). → 더 많은 질의로 튜닝 필요, 필요 시 `rerank_enabled=False` 한 번에 롤백.
- 첫 사용 시 모델 다운로드(수백 MB) 지연 — 임베더와 동일. 컨테이너는 `hf_cache` 볼륨으로 warm 유지.
- 리랭커 점수는 unbounded 로짓 → 절대 임계값(gap)에 못 씀. gap 은 코사인 유지로 회피(위).

## 결과
- `infrastructure/embedding/reranker.py`(신규) + `__init__` export. `shared/config/settings.py`: `rerank_enabled/reranker_model/rerank_pool`.
- `apps/wiki_pipeline.py`: `hybrid_search()`/`apply_rerank()`/`_build_reranker()`, `ask()` 배선. `apps/mcp/queries.py`·`server.py` 리랭커 인자.
- 유닛 4건(FakeReranker + apply_rerank). 라이브 A/B: 정밀 질의는 top-1 분리 대폭 개선(0.109 vs −1.096), 콜로퀴얼은 상기 절충.
