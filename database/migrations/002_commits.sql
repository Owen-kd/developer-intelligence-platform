-- 002_commits.sql — Git 커밋 + 이슈↔커밋 링크
-- 참조: .ai/architecture/database-design.md

CREATE TABLE IF NOT EXISTS commits (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sha           text NOT NULL UNIQUE,
    author        text,
    message       text NOT NULL,
    committed_at  timestamptz,
    synced_at     timestamptz NOT NULL DEFAULT now()
);

-- 이슈 ↔ 커밋 링크 (다대다)
CREATE TABLE IF NOT EXISTS issue_commits (
    issue_id   uuid NOT NULL REFERENCES issues (id) ON DELETE CASCADE,
    commit_id  uuid NOT NULL REFERENCES commits (id) ON DELETE CASCADE,
    PRIMARY KEY (issue_id, commit_id)
);

CREATE INDEX IF NOT EXISTS idx_issue_commits_commit_id ON issue_commits (commit_id);
