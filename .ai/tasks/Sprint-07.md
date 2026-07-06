# Sprint-07 — 임베딩 · 검색 · 그래프

- 상태: Todo
- Phase / Milestone: Phase 2 (Knowledge & Context) / M2
- 의존성: **Sprint-05** (Knowledge 존재)
- 병렬: Sprint-06 · 이후 Sprint-10(Impact가 그래프 소비)

## 문제 (Discovery)
Knowledge/Context 조립의 품질을 위해 **의미 검색(임베딩)** 과 **관계 탐색(Neo4j 그래프)** 이 필요하다(roadmap Phase 2).

## 범위
- 하는 것:
  - `infrastructure/neo4j/client.py`: 그래프 연결(외부 호출 격리).
  - `modules/graph`: 코드↔이슈↔의존성 노드/관계 적재(`(:Issue)-[:TOUCHES]->(:File)`, `(:Commit)-[:FIXES]->(:Issue)`).
  - `modules/embedding`: Knowledge 임베딩 생성(worker).
  - `modules/search`: 임베딩 기반 최소 검색 경로 → Context Builder가 활용 가능.
  - `apps/worker`(embedding/graph) 진입점 연결.
- 안 하는 것(Non-goals):
  - 전체 코드 정적분석/의존성 그래프 완전판, 랭킹 고도화(후속).

## 성공 기준 (DoD)
- [ ] Knowledge 임베딩 생성 → 유사 Knowledge 검색이 동작(최소 경로).
- [ ] 이슈/커밋/파일 관계가 Neo4j에 적재되고 질의된다.
- [ ] 외부(embedding/neo4j) 호출은 `infrastructure` 경유. unit은 목킹. ruff/mypy/pytest 통과.

## 설계 메모 (Design)
- Neo4j는 **파생 그래프**(진실 원천은 Postgres)([../architecture/database-design.md]).
- 임베딩 모델/저장소 선택은 아키텍처 결정 → Approval.

## Approval Gate — 착수 전
- **[APR-004]** Vector store 선택(pgvector vs 외부) (Pending).
- **[APR-003]** 의존성(neo4j driver, 임베딩 라이브러리/모델) → ADR (Pending).
- 임베딩을 외부 LLM 임베딩 API로 할 경우 **[APR-005]** 데이터 전송 정책도 적용.

## 체크리스트
- [ ] 구현 (neo4j infra → graph → embedding → search)
- [ ] 테스트
- [ ] 리뷰
- [ ] `state`/`milestones`(M2) 갱신

## 회고
- 잘된 것:
- 개선할 것:
