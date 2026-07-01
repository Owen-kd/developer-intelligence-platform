# Onboarding — Repository Tour

> 저장소 어디에 무엇이 있는지 빠르게 파악한다. 상세 규칙은 [../architecture/folder-structure.md](../architecture/folder-structure.md).

## 최상위
```
apps/            실행 진입점 (api / worker / scheduler / cli)
modules/         비즈니스 모듈 — 각자 DDD-lite(application/domain/infrastructure/presentation)
platform/        플랫폼 코어 (event / workflow / registry / auth / audit / context)
infrastructure/  외부 연동 어댑터 (jira / git / openai / anthropic / neo4j / postgres / redis)
shared/          공통 (config / logger / exceptions / constants / utils / models)
database/        migrations / seed / schema
prompts/         코드 밖 프롬프트 자산 (triage/impact/comment/review/knowledge/incident)
tests/           unit / integration / e2e
docker/          postgres / neo4j / redis
.ai/             AI Operating System (아래)
```

## 코드를 만질 때 진입 지점
| 하고 싶은 것 | 어디로 |
|--------------|--------|
| API 엔드포인트 추가 | `apps/api/` (라우터) → `modules/<x>/application/service.py` |
| 새 비즈니스 능력 | `modules/<x>/` (DDD 4계층) |
| 외부 시스템 연동 | `infrastructure/<system>/` |
| 모듈 간 연동 | `platform/event` (EventBus) |
| LLM/Agent | `platform/{context,workflow}` + `infrastructure/{openai,anthropic}` |
| 설정 | `shared/config/settings.py` (+ `.env.example`) |

## `.ai/` 지도 (AI Operating System)
```
core/         헌법 (거의 안 바뀜)
philosophy/   왜 이렇게 설계했나
glossary/     정본 용어
context/      지금의 프로젝트 (overview/current-task/tech-stack/env)
architecture/ 목표 구조 (system/folder/db/event/agent/api/context-engine/knowledge-lifecycle)
contracts/    구현 계약 (module/event/knowledge/agent/api)
standards/    개발 표준 (branch/commit/pr/review/testing)
workflow/     개발 프로세스 5단계
playbooks/    작업별 실행 절차
planning/     roadmap / milestones / backlog
state/        현재 상태 (current-architecture/known-limitations/technical-debt)
decisions/    ADR
onboarding/   여기 (getting-started/repository-tour)
references/   기술 참고 (jira-api/fastapi/postgres)
prompts/      AI 프롬프트 지침
knowledge/    회사/도메인 지식 (채워나감)
tasks/ reviews/ templates/
```

## 팁
- "지금 무엇이 실제로 구현됐나"는 항상 [../state/current-architecture.md](../state/current-architecture.md) 를 신뢰한다(목표 구조와 다를 수 있음).
- 용어가 헷갈리면 [../glossary/terms.md](../glossary/terms.md).

→ 이전: [getting-started.md](getting-started.md)
