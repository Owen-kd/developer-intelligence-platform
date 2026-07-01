# .ai — AI Operating System

Claude Code · GPT · Codex · Cursor 가 공통으로 따르는 **AI 운영체계**이자 **Single Source of Truth**.
새로 합류한 AI는 [onboarding/getting-started.md](onboarding/getting-started.md) 에서 시작한다.

## 읽는 순서 (권장)
`onboarding/` → `philosophy/` → `glossary/` → `core/` → `state/` → `context/current-task.md`

## 구조
| 폴더 | 역할 | 성격 |
|------|------|------|
| `onboarding/` | 새 AI가 가장 먼저 (getting-started / repository-tour) | 안정적 |
| `philosophy/` | 왜 이렇게 설계했나 (knowledge-first / event-driven / context-over-prompt) | 거의 안 바뀜 |
| `glossary/` | 정본 용어 (terms) | 안정적 |
| `core/` | AI의 헌법 (system / architecture / coding / naming) | 거의 안 바뀜 |
| `context/` | 지금의 프로젝트 (overview / current-task / tech-stack / env) | 자주 갱신 |
| `architecture/` | 목표 구조 (system / folder / db / event / agent / api / context-engine / knowledge-lifecycle) | 설계 변화 시 |
| `contracts/` | 구현 계약 (module / event / knowledge / agent / api) | 안정적 |
| `standards/` | 개발 표준 (branch / commit / pull-request / review / testing) | 안정적 |
| `workflow/` | 개발 프로세스 5단계 (01~05) | 거의 안 바뀜 |
| `playbooks/` | ⭐ 작업별 실행 절차 (jira / impact / incident / review / release) | 핵심 |
| `planning/` | roadmap / milestones / backlog | 자주 갱신 |
| `state/` | 현재 상태 (current-architecture / known-limitations / technical-debt) | 자주 갱신 |
| `decisions/` | ADR (되돌리기 어려운 결정) | 결정마다 |
| `prompts/` | AI 프롬프트 지침 (architect / review / triage / comment) | 수시 |
| `knowledge/` | 회사/도메인 지식 (jira / git / db / incident / business) | 채워나감 |
| `tasks/` | 스프린트/태스크 | 수시 |
| `reviews/` | 리뷰 기록 | 리뷰마다 |
| `templates/` | adr / task / review / incident 템플릿 | 안정적 |
| `references/` | 기술 참고 (jira-api / fastapi / postgres) | 수시 |

## 개발 흐름
```
Discovery → Design → Implementation → Review → Release
(workflow/01) (02)      (03)           (04)      (05)
```
설계와 구현, 구현과 리뷰의 주체를 분리한다(예: GPT 설계 → Claude 구현 → GPT 리뷰).

## 원칙
> **Knowledge First. Context Before AI. AI Last.**
- 계층 규칙과 용어는 재정의하지 않고 이 `.ai` 를 참조한다(Single Source of Truth).

## 시작점
- 온보딩: [onboarding/getting-started.md](onboarding/getting-started.md)
- 최상위 규칙: [core/system.md](core/system.md)
- 지금 뭘 하는 중인가: [context/current-task.md](context/current-task.md)
- 지금 실제로 뭐가 됐나: [state/current-architecture.md](state/current-architecture.md)
