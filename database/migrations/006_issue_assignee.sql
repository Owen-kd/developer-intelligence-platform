-- 006_issue_assignee.sql — 이슈 담당자(assignee) 추가 (enrich: "누가")
-- PII 최소화: 표시명(displayName)만 저장 — APR-002.

ALTER TABLE issues ADD COLUMN IF NOT EXISTS assignee text;
