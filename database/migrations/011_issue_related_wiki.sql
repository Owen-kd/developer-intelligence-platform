-- 011_issue_related_wiki.sql — 루프3-Push: 이슈에 자동 연결된 유사 과거 위키
-- 새 이슈가 들어오면 의미 유사한 과거 위키를 찾아 여기에 링크한다(팀 간 지식 격차 해소).
-- 내부 저장만 — 실 Jira 코멘트 쓰기는 별도 승인 게이트(target-service #5).

CREATE TABLE IF NOT EXISTS issue_related_wiki (
    issue_id uuid NOT NULL,
    wiki_id uuid NOT NULL,
    score double precision NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (issue_id, wiki_id)
);

CREATE INDEX IF NOT EXISTS idx_related_issue ON issue_related_wiki (issue_id);
