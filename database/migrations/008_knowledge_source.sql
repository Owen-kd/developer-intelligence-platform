-- 008_knowledge_source.sql — 지식 신뢰등급(source)
-- 'verified'=전문가 작성(검증됨, 우선) / 'derived'=자동 추출·정제.

ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'derived';

CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge (source);
