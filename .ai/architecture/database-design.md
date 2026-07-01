# Database Design

> 초기 골격 문서. 스키마가 확정되면 `database/schema/` 와 함께 갱신한다.

## 저장소 역할 분리
- **Postgres** — 정형/트랜잭션 데이터가 진실의 원천(source of truth).
- **Neo4j** — 관계 탐색용 파생 그래프(코드↔이슈↔의존성).
- **Redis** — 캐시/임시 상태. 영속 진실 원천으로 쓰지 않는다.

## Postgres — 초기 테이블(안)
| 테이블 | 목적 | 핵심 컬럼 |
|--------|------|-----------|
| `issues` | Jira 이슈 스냅샷 | `id`, `jira_key`, `type`, `status`, `priority`, `summary`, `created_at`, `updated_at` |
| `comments` | 이슈 코멘트 | `id`, `issue_id(FK)`, `author`, `body`, `created_at` |
| `commits` | Git 커밋 메타 | `id`, `sha`, `author`, `message`, `committed_at` |
| `issue_commits` | 이슈↔커밋 링크 | `issue_id`, `commit_id` |
| `impact_reports` | 영향도 분석 결과 | `id`, `issue_id(FK)`, `summary`, `payload(jsonb)`, `created_at` |
| `events` | 감사/이벤트 로그 | `id`, `name`, `payload(jsonb)`, `occurred_at` |

## 규칙
- 테이블 복수형 `snake_case`, PK `id`, FK `<단수>_id`.
- 시간 컬럼은 UTC `timestamptz`.
- 반정형 데이터는 `jsonb`.
- 스키마 변경은 `database/migrations/NNN_*.sql` 로만. 앱이 임의로 DDL 하지 않는다.

## Neo4j — 노드/관계(안)
- 노드: `(:Issue)`, `(:Commit)`, `(:File)`, `(:Service)`
- 관계: `(:Issue)-[:TOUCHES]->(:File)`, `(:File)-[:DEPENDS_ON]->(:File)`, `(:Commit)-[:FIXES]->(:Issue)`
