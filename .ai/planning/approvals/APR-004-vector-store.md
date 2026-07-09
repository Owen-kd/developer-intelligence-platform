# APR-004 — Vector Store 선택 (pgvector vs 외부)

- 상태: **Approved — pgvector** (오너 지시 2026-07-08)
- 요청일: 2026-07-07
- 승인일: 2026-07-08 (오너 지시로 pgvector 확정 — 사용자 비전 덱 slide 08 "Embeddings: pgvector" 와 일치)
- 요청자: Project Planner (AI)
- 관련 Sprint: Sprint-07 (임베딩·검색)
- 관련 ADR: [ADR-009](../../decisions/ADR-009-local-embedding-pgvector.md)

## 요청 요약
Knowledge 임베딩을 저장·검색할 **벡터 저장소**를 확정한다. 데이터 아키텍처 결정이라 사람 승인이 필요하다.

## 왜 사람이 결정해야 하나
- 저장소 추가는 운영 부담·비용·백업/마이그레이션에 영향. 되돌리기 비싸다.
- 현 tech-stack은 Postgres/Neo4j/Redis. 벡터 저장소는 미정.

## 선택지
1. **(추천) pgvector** — 기존 Postgres에 확장. 새 인프라 0, 진실 원천과 동거, 규모 초기 충분.
2. Neo4j 벡터 인덱스 — 이미 도입할 Neo4j 활용, 그래프+벡터 통합.
3. 외부 전용 벡터 DB(예: Qdrant/pgvector 외) — 확장성↑, 운영 컴포넌트 추가.

## 절충
- pgvector: 초기 단순·저비용, 초대규모에서 한계 → 그때 분리(YAGNI에 부합).
- 외부 전용: 조기 복잡도·비용 증가(현 단계 과설계 위험).

## 영향
- 승인 시: Sprint-07이 선택 저장소로 임베딩/검색 구현, `docker-compose`/마이그레이션 반영.
- 미승인 시: Sprint-07 착수 불가.

## 승인 체크
- [x] 승인 (선택: **pgvector**) — 오너 지시 2026-07-08
- [ ] 조건부 승인 (조건: __________)
- [ ] 거부 / 보류
