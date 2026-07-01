# .ai — AI 개발 컨텍스트

Claude Code · GPT · Codex · Cursor 가 공통으로 따르는 개발 컨텍스트.
새 세션을 시작하는 AI는 `core/` → `context/` → 해당 `playbooks/` 순으로 읽는다.

| 폴더 | 역할 | 성격 |
|------|------|------|
| `core/` | AI의 헌법 (system / coding / architecture / naming) | 거의 안 바뀜 |
| `context/` | 지금의 프로젝트 (overview / current-task / roadmap / tech-stack / env) | 자주 갱신 |
| `architecture/` | 전체 구조 (system / folder / db / event / agent / api) | 설계 변화 시 |
| `workflow/` | AI가 항상 따르는 개발 프로세스 (01~05) | 거의 안 바뀜 |
| `playbooks/` | ⭐ 작업별 실행 절차 (jira/impact/incident/review/release) | 핵심 |
| `prompts/` | 역할별 프롬프트 자산 | 수시 |
| `knowledge/` | 회사/도메인 지식 (jira/git/db/incident/business) | 채워나감 |
| `decisions/` | ADR (되돌리기 어려운 결정 기록) | 결정마다 |
| `tasks/` | 스프린트/태스크 | 수시 |
| `reviews/` | 리뷰 기록 | 리뷰마다 |
| `templates/` | adr / task / review / incident 템플릿 | 안정적 |

## 개발 흐름
```
Discovery → Design → Implementation → Review → Release
(workflow/01) (02)      (03)           (04)      (05)
```
설계와 구현, 구현과 리뷰의 주체를 분리한다(예: GPT 설계 → Claude 구현 → GPT 리뷰).

## 시작점
- 최상위 규칙: [core/system.md](core/system.md)
- 지금 뭘 하는 중인가: [context/current-task.md](context/current-task.md)
