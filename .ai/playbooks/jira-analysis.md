# Playbook — Jira Analysis / Triage (이슈 분류)

> 새 이슈를 자동 분류·우선순위화·라우팅한다.

## 입력
- `issue_key` 또는 신규 이슈 웹훅 페이로드

## 절차
### 1. 이슈 수집
- 제목/본문/타입/현재 상태/신고자 수집 (infrastructure/jira).

### 2. 정규화
- 회사 이슈 타입 규약([../knowledge/jira/])에 매핑.
- 중복/유사 이슈 검색(`modules/search`).

### 3. 분류
- 카테고리(버그/기능/작업/장애), 영향 컴포넌트 추정.
- 프롬프트: `prompts/triage/classify.md`.

### 4. 우선순위 산정
- 심각도 × 영향 범위 × 긴급도. 근거를 남긴다.

### 5. 라우팅 제안
- 담당 팀/모듈, 필요한 후속 분석(예: Impact Analysis) 추천.

### 6. 결과 반영
- 분류/우선순위/근거를 이슈에 코멘트 또는 리포트로. `ImpactAnalyzed`/`IssueTriaged` 이벤트 발행.

## 규칙
- 회사 특화 규약(이슈 타입/커스텀 필드)은 코드가 아니라 [../knowledge/jira/] 에서 읽는다.
- LLM 분류 결과는 스키마 검증 후 사용.
