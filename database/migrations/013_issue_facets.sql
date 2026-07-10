-- 013_issue_facets.sql — 이슈 Facet 분류 레이어 (ADR-015)
-- 이슈 원본(issues)은 불변. 분류는 여기에 얹는 파생 레이어(재분류=upsert).
-- 6축: 도메인/기능영역/액션/채널/유형/팀/영역. method=분류 출처(rule|llm).

CREATE TABLE IF NOT EXISTS issue_facets (
    issue_id uuid PRIMARY KEY,
    domain text NOT NULL DEFAULT '미상',
    feature_area text NOT NULL DEFAULT '미상',
    action text NOT NULL DEFAULT '미상',
    channel text NOT NULL DEFAULT '공통',
    issue_type text NOT NULL DEFAULT '미상',
    team text NOT NULL DEFAULT '미상',
    area text NOT NULL DEFAULT '미상',
    method text NOT NULL DEFAULT 'rule',
    classified_at timestamptz NOT NULL DEFAULT now()
);

-- 둘러보기(도메인>기능영역>액션) + 축별 필터 인덱스
CREATE INDEX IF NOT EXISTS idx_facets_browse ON issue_facets (domain, feature_area, action);
CREATE INDEX IF NOT EXISTS idx_facets_channel ON issue_facets (channel);
CREATE INDEX IF NOT EXISTS idx_facets_type ON issue_facets (issue_type);
CREATE INDEX IF NOT EXISTS idx_facets_team ON issue_facets (team);
