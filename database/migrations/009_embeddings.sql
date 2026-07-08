-- 009_embeddings.sql — 지식 임베딩(벡터 검색용) — ADR-009
-- pgvector 확장 + knowledge.embedding 컬럼 + 코사인 HNSW 인덱스.
-- 차원 1024 = intfloat/multilingual-e5-large (settings.embedding_dim 와 일치해야 함).
-- 모델/차원 변경 시: 이 컬럼을 DROP 후 새 차원으로 재생성하는 신규 마이그레이션 필요.

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS embedding vector(1024);

-- 코사인 거리(<=>) 검색용 HNSW 인덱스. NULL(미임베딩) 행은 인덱스에서 제외됨.
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding
    ON knowledge USING hnsw (embedding vector_cosine_ops);
