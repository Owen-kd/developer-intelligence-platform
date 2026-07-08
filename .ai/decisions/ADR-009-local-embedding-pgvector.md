# ADR-009 — 로컬 임베딩(fastembed) + pgvector 벡터 저장

- 상태: Accepted
- 날짜: 2026-07-08
- 관련: [APR-004](../planning/approvals/APR-004-vector-store.md) · [APR-005](../planning/approvals/APR-005-llm-vendor-data.md) · Sprint-07(임베딩·검색) · [ADR-006](ADR-006-anthropic-adapter.md)

## 맥락
오너 지시(2026-07-08): 도서관의 Jira 이슈를 **LLM으로 "위키 문서"화 → 벡터 DB 적재 → RAG 유사검색**.
이는 사용자 비전 덱 "AI DevOps Platform"의 첫 실전 조각이다(덱 slide 06 Vector Search, slide 08 **"Embeddings: pgvector"** 명시, slide 12 지식 자산화).
현재 도서관 검색은 `ILIKE` 키워드 매칭(의미검색 아님). 임베딩/벡터 인프라는 전무.

두 가지 외부/인프라 결정이 필요하다: (1) 임베딩 모델, (2) 벡터 저장소. 되돌리기 비싸고 의존성·비용에 영향 → ADR.

## 결정

### 1. 벡터 저장소 = pgvector
- 이미 운영 중인 Postgres에 `vector` 확장만 추가. 새 서비스 0, 진실 원천(issues/knowledge)과 동거.
- `knowledge` 테이블에 `embedding vector(N)` 컬럼 추가(위키는 Knowledge 행). 코사인 거리 `<=>` 로 top-k.
- [APR-004] 추천안(pgvector)과 일치 → 본 ADR로 승인 반영.
- docker 이미지 `postgres:16-alpine` → `pgvector/pgvector:pg16`(PG16 동일 메이저, 명명 볼륨 `pg_data` 유지 → 데이터 보존).

### 2. 임베딩 모델 = 로컬(fastembed, multilingual-e5)
- 오너 선택: **로컬 임베딩**(API 키 불필요, 외부 전송 0 → APR-005 데이터 반출 부담 없음).
- 라이브러리 = **`fastembed`**(ONNX 런타임). `sentence-transformers`(torch ~2GB)를 피해 의존성 경량화.
- 기본 모델 = `intfloat/multilingual-e5-large`(dim 1024, 한국어 포함 다국어). 최초 1회 모델 파일 다운로드(~1GB, 이후 캐시).
- `infrastructure/embedding/`에 `Embedder` 포트 + `FastEmbedEmbedder` 어댑터 + `FakeEmbedder`(결정적, 테스트용). LLMClient와 동일한 포트-어댑터 패턴.

## 근거
- pgvector: 초기 단순·저비용, 초대규모 시 분리(YAGNI). 백업/운영이 기존 Postgres에 흡수됨.
- 로컬 임베딩: 이슈 본문(사내 데이터)을 외부로 보내지 않음 → 규정 리스크 최소. 키 발급/과금 없음.
- fastembed: torch 미포함 → 컨테이너·설치 경량. e5 계열은 한국어 혼용 텍스트에서 실용 성능.
- 포트 뒤 어댑터 → 후일 OpenAI 임베딩/다른 모델로 교체해도 modules/platform 불변.

## 절충 / 리스크
- 모델 교체 시 임베딩 차원(N)이 바뀌면 컬럼 재생성(신규 마이그레이션) + 재임베딩 필요. → 차원은 설정으로 노출, 기본 1024 고정.
- 최초 실행 시 모델 다운로드(네트워크·디스크). 오프라인 CI는 `FakeEmbedder`로 결정적 테스트.
- fastembed 타입 스텁 부재 → mypy `ignore_missing_imports=true`(기존 설정)로 흡수.
- pgvector 이미지 교체는 컨테이너 재생성 필요(데이터는 볼륨 유지되나 1회 다운타임).

## 결과
- `docker-compose.yml`: postgres 이미지 교체.
- `database/migrations/009_embeddings.sql`: `CREATE EXTENSION vector` + `knowledge.embedding` + ivfflat 인덱스.
- `pyproject.toml`: `fastembed` 런타임 의존성 추가.
- `shared/config/settings.py`: `embedding_model` / `embedding_dim`.
- `infrastructure/embedding/`: 포트+어댑터 신규.
- 위키 생성: `modules/knowledge/application/wiki_service.py` + `prompts/knowledge/wiki.md`.
- 검색: `apps/mcp/queries.py` 의미검색 경로 + 저장소 임베딩 저장/조회.
