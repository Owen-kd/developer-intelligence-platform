# Naming Conventions

## Python
- 모듈/패키지/파일: `snake_case` (`issue_service.py`)
- 클래스: `PascalCase` (`IssueService`, `JiraClient`)
- 함수/변수: `snake_case`
- 상수: `UPPER_SNAKE_CASE` (`shared/constants/`)
- 프라이빗: 앞에 `_` (`_engine`)

## DDD 계층별 파일 관례 (modules/<x>/)
| 계층 | 파일 | 대표 클래스 |
|------|------|-------------|
| application | `service.py` | `<Name>Service` |
| domain | `entity.py`, `repository.py` | `<Name>`, `<Name>Repository`(추상) |
| infrastructure | `client.py`, `repository.py` | `<Name>Client`, `<Name>RepositoryImpl` |
| presentation | `controller.py`, `dto.py` | `<Name>Controller`, `<Name>Request/Response` |

## 이벤트
- 이벤트명: 과거형 명사구 `PascalCase` — `IssueCreated`, `CommentAdded`, `ImpactAnalyzed`.
- 페이로드 DTO: `<Event>Payload`.

## Agent · Prompt
- Agent 이름: 역할 기반 kebab — `triage-agent`, `impact-agent`, `review-agent`.
- 프롬프트 파일: `prompts/<domain>/<purpose>.md` — `prompts/triage/classify.md`.

## API
- 경로: 복수형 명사, kebab — `/issues`, `/impact-analyses`.
- 시스템 엔드포인트: `/health`, `/ready`, `/version`.

## DB
- 테이블: 복수형 `snake_case` — `issues`, `comments`, `impact_reports`.
- 컬럼: `snake_case`. PK `id`, FK `<단수>_id` (`issue_id`).
- 마이그레이션 파일: `NNN_설명.sql` (`001_init.sql`).

## 브랜치 · 커밋
- 브랜치: `feature/<요약>`, `fix/<요약>`, `chore/<요약>`.
- ADR: `.ai/decisions/ADR-NNN-<주제>.md`.
