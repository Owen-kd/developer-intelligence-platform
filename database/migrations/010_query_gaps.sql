-- 010_query_gaps.sql — 되먹임(feedback) 씨앗: 답 못한/약한 질문 기록
-- /ask 가 근거를 못 찾거나 유사도가 낮을 때 질문을 남긴다 → "무엇을 위키화·수집할지" 신호.
-- (target-service 되먹임 루프)

CREATE TABLE IF NOT EXISTS query_gaps (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    question text NOT NULL,
    hit_count int NOT NULL DEFAULT 0,
    top_score double precision NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_query_gaps_created ON query_gaps (created_at DESC);
