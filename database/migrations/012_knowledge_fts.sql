-- 012_knowledge_fts.sql — 하이브리드 검색용 전문검색(FTS) 인덱스 (BM25 arm)
-- 벡터(pgvector)는 의미를, FTS 는 정확 식별자(option_code/vendorItemId/GTIN/쿠팡/옵션)를 잡는다.
-- 'simple' config: 형태소 사전 없이 토큰화 → 한국어 단어·영문 식별자 정확 매칭에 적합.
-- 생성 컬럼(STORED) → 기존 위키도 자동 채워지고, 이후 자동 동기화.

ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS tsv tsvector
    GENERATED ALWAYS AS (
        to_tsvector(
            'simple',
            coalesce(summary, '') || ' ' ||
            coalesce(body->>'content', '') || ' ' ||
            coalesce(body->>'symptom', '') || ' ' ||
            coalesce(body->>'root_cause', '') || ' ' ||
            coalesce(body->>'resolution', '') || ' ' ||
            coalesce(body->>'code_refs', '')
        )
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_knowledge_tsv ON knowledge USING gin (tsv);
