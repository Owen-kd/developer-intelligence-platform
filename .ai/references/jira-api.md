# Reference — Jira API

> DIP에서 Jira를 어떻게 연동할지에 대한 간략 참고. **연동 코드는 아직 미구현**(설계·계획 단계).
> 지식 관점: Jira 이슈는 원천 데이터 → Event/Timeline → Knowledge 로 승격된다([../architecture/knowledge-lifecycle.md]).

## 프로젝트 내 위치 (예정)
- 연동 코드: `infrastructure/jira/` (Collector가 사용).
- 비즈니스 로직: `modules/jira/` (DDD 4계층).
- 회사별 규약(이슈 타입/커스텀 필드/워크플로우): `.ai/knowledge/jira/` (채워나감).

## 인증 (Jira Cloud 기준)
- 방식: Basic Auth = `email` + **API Token**.
- 환경변수(`.env.example`): `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`.
- 토큰은 절대 커밋 금지 — `infrastructure/` 에서 설정을 통해 주입.

## 주로 쓸 엔드포인트 (REST v3, 읽기 우선)
| 목적 | 개략 |
|------|------|
| 이슈 조회 | `GET /rest/api/3/issue/{key}` |
| 이슈 검색(JQL) | `GET /rest/api/3/search?jql=...` |
| 코멘트 조회 | `GET /rest/api/3/issue/{key}/comment` |
| 변경 이력 | `GET /rest/api/3/issue/{key}?expand=changelog` |

## 연동 규칙 (프로젝트)
- 호출은 `infrastructure/jira/` 에만(모듈에서 직접 호출 금지).
- 수집 결과는 상태 저장이 아니라 **Event**로 표현(예: `IssueCollected`).
- 원천 응답을 LLM에 직접 넣지 않는다 — Knowledge 승격 후 Context Builder 경유.
- 초기에는 **읽기 전용** 수집만. 쓰기(코멘트 작성 등)는 별도 결정(ADR).

## 외부 문서
- Jira Cloud REST v3: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- API 토큰 관리: https://id.atlassian.com/manage-profile/security/api-tokens
