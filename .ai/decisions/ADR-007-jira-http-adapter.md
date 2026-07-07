# ADR-007 — 실 Jira 수집 어댑터(HTTP, REST v3)

- 상태: Accepted
- 날짜: 2026-07-07
- 관련: [APR-002](../planning/approvals/APR-002-jira-access-pii.md) · [APR-003](../planning/approvals/APR-003-dependencies.md) · [Sprint-14](../tasks/Sprint-14.md) · [references/jira-api](../references/jira-api.md)

## 맥락
Sprint-14 ② 는 `FakeJiraClient` 를 실 어댑터로 교체한다. 실 PA20 인스턴스 탐침 결과:
- 인증 OK(Basic: email + API token).
- **classic `GET /rest/api/3/search` 는 410 Gone** — 제거됨.
- **enhanced `GET /rest/api/3/search/jql` 사용**(토큰 페이지네이션). 코멘트 본문은 ADF(JSON).

## 결정
`infrastructure/jira/client.py` 에 **`HttpJiraClient(JiraClient)`** 추가. 런타임 의존성 **`httpx`**([APR-003] 승인분).
- 엔드포인트: `/rest/api/3/search/jql`, JQL `project=<KEY> ORDER BY created DESC`.
- 필드: `summary,status,issuetype,priority,created,updated,comment`.
- 코멘트 본문은 ADF→평문 추출(`_adf_to_text`).
- **읽기 전용**. 수집은 **bounded**(최근 N개, 기본 10) — 전량 증분 동기화는 후속.

## 근거
- 공식 SDK 대신 httpx 직접 → 의존성 최소([coding-guidelines]: 표준/httpx 우선), 엔드포인트 1개.
- 포트(`JiraClient.fetch_issues`) 뒤 교체 → 모듈/서비스 코드 변경 0.
- classic `/search` 제거(410) 대응이 강제 사항.

## 절충 / 리스크 / PII
- **PII 최소화**([APR-002]): 작성자는 표시명(`displayName`)만 저장, 이메일/계정ID 미저장.
- bounded 수집 → 전량 동기화·증분 커서·rate limit 처리(429)는 후속 과제.
- ADF 추출은 텍스트 노드 중심(첨부/멘션 등은 평문화 손실 가능) — 요약 용도로 충분.

## 결과
- `shared/config/settings.py`: `jira_base_url/email/api_token/project_key/max_issues` + `jira_configured`.
- `apps/composition_pg`: 설정 있으면 `HttpJiraClient`, 없으면 `FakeJiraClient`(스왑만).
- 시크릿은 `.env`(gitignore), `.env.example` 만 커밋.
