-- 001_init.sql — 초기 스키마 (issues, comments, events)
-- 규약: 복수형 snake_case 테이블, PK id, FK <단수>_id, 시간은 timestamptz(UTC), 반정형은 jsonb.
-- 참조: .ai/architecture/database-design.md

-- 이슈 스냅샷 (Jira 원천)
CREATE TABLE IF NOT EXISTS issues (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    jira_key    text NOT NULL UNIQUE,
    type        text,
    status      text,
    priority    text,
    summary     text NOT NULL,
    created_at  timestamptz,
    updated_at  timestamptz,
    synced_at   timestamptz NOT NULL DEFAULT now()
);

-- 이슈 코멘트
CREATE TABLE IF NOT EXISTS comments (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id     uuid NOT NULL REFERENCES issues (id) ON DELETE CASCADE,
    external_id  text NOT NULL,                 -- Jira 코멘트 id (멱등 upsert 키)
    author       text,
    body         text NOT NULL,
    created_at   timestamptz,
    UNIQUE (issue_id, external_id)
);

CREATE INDEX IF NOT EXISTS idx_comments_issue_id ON comments (issue_id);

-- 이벤트 로그 (append-only, 불변)
CREATE TABLE IF NOT EXISTS events (
    id           text PRIMARY KEY,             -- Event.event_id
    name         text NOT NULL,
    payload      jsonb NOT NULL DEFAULT '{}'::jsonb,
    occurred_at  timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_name ON events (name);
CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events (occurred_at);
