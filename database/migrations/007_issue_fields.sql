-- 007_issue_fields.sql — 이슈 필드 확장 (enrich: 본문 + glossary급 구조화 필드)
-- description=본문(원천 보존, 2차 LLM 요약용) / labels·components=도메인 태그(서가) / reporter=문의자.

ALTER TABLE issues ADD COLUMN IF NOT EXISTS description text;
ALTER TABLE issues ADD COLUMN IF NOT EXISTS labels     jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE issues ADD COLUMN IF NOT EXISTS components jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE issues ADD COLUMN IF NOT EXISTS reporter   text;
