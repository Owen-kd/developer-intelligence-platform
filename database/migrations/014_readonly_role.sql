-- 014_readonly_role.sql — 조회 전용 롤(dip_reader): 질의 서빙 계층용 (멀티유저 보안 게이트, ADR-010 동반)
--
-- 목적: 40인 서빙(API/MCP)이 원천 데이터(knowledge/issues 등)를 변조·삭제하지 못하게 최소권한.
--   - 조회는 허용하되, 쓰기는 되먹임 로깅(query_gaps)만.
--   - 원천 고객 PII 저장소인 comments 는 서빙이 읽지 않으므로 조회 자체를 차단(심층 방어).
--   - 쓰기 파이프라인(worker/scheduler: 수집·위키생성·백필)은 기존 dip 롤 사용.
-- 배포: 비밀번호는 시크릿으로 별도 설정 → `ALTER ROLE dip_reader PASSWORD '<secret>';` (레포에 넣지 않음).
--   API 는 dip_reader DSN 으로 접속, worker/scheduler 는 dip DSN 유지.
-- ※ $$ 블록 포함 → psql 로 적용(앱 run_script 의 세미콜론 분할과 충돌 방지).

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dip_reader') THEN
        CREATE ROLE dip_reader LOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO dip_reader;

-- 전체 테이블 조회 허용(서빙이 필요로 하는 knowledge/issues/facets/commits 등)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dip_reader;
-- 향후 생성 테이블도 기본 SELECT
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO dip_reader;

-- 되먹임 로깅(질의 서빙이 남기는 유일한 쓰기)만 INSERT 허용
GRANT INSERT ON query_gaps TO dip_reader;

-- 원천 고객 PII(코멘트)는 서빙 계층에서 불필요 → 조회 차단(심층 방어)
REVOKE SELECT ON comments FROM dip_reader;
