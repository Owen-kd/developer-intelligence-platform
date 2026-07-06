-- 003_knowledge.sql — Knowledge Library
-- 참조: .ai/architecture/knowledge-lifecycle.md · .ai/contracts/knowledge-contract.md

CREATE TABLE IF NOT EXISTS knowledge (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    type        text NOT NULL,
    issue_id    uuid REFERENCES issues (id) ON DELETE CASCADE,
    summary     text NOT NULL,
    body        jsonb NOT NULL DEFAULT '{}'::jsonb,
    sources     jsonb NOT NULL DEFAULT '[]'::jsonb,   -- 출처(Event/Knowledge id) 보존
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_issue_id ON knowledge (issue_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge (type);
