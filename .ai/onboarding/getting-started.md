# Onboarding — Getting Started

> 새로 합류한 AI/개발자가 **가장 먼저** 읽는 문서. 여기서 시작해 링크를 따라가라.

## 1. DIP가 무엇인가 (30초)
회사의 운영 경험(Jira·Git·장애)을 **재사용 가능한 Knowledge**로 축적하는 플랫폼.
AI 챗봇이 아니다. 표어: **Knowledge First. Context Before AI. AI Last.**
→ [../context/project-overview.md](../context/project-overview.md)

## 2. 반드시 읽을 순서
1. **철학** — 왜 이렇게 설계했나: [../philosophy/](../philosophy/) (knowledge-first → event-driven → context-over-prompt)
2. **용어** — 정본 어휘: [../glossary/terms.md](../glossary/terms.md)
3. **헌법** — 절대 규칙: [../core/system.md](../core/system.md) · [../core/architecture-principles.md](../core/architecture-principles.md)
4. **구조** — 어디에 뭐가 있나: [repository-tour.md](repository-tour.md)
5. **현재 상태** — 지금 실제로 뭐가 됐나: [../state/current-architecture.md](../state/current-architecture.md)
6. **지금 할 일** — [../context/current-task.md](../context/current-task.md) · [../planning/milestones.md](../planning/milestones.md)

## 3. 작업하는 법
- 모든 작업은 워크플로우를 따른다: Discovery→Design→Implementation→Review→Release ([../workflow/](../workflow/)).
- 작업 유형별 절차는 [../playbooks/](../playbooks/).
- 지켜야 할 계약은 [../contracts/](../contracts/), 표준은 [../standards/](../standards/).

## 4. 로컬 실행
```bash
docker compose up -d                     # postgres/neo4j/redis
pip install -e ".[dev]"                   # 의존성
cp .env.example .env                      # 환경변수
uvicorn apps.api.main:app --reload        # API → http://localhost:8000/health
ruff check . && mypy . && pytest -q       # 품질 게이트
```
> 참고: 로컬 Python은 3.11+ 필요([../state/known-limitations.md] 참조).

## 5. 절대 규칙 (요약)
- 의존성 방향: `apps→modules→platform→infrastructure→shared` (역방향 금지).
- 외부 호출은 `infrastructure/` 경유. 모듈끼리 직접 import 금지(Event 사용).
- 원천 데이터를 LLM에 직접 넣지 않는다(Context Builder 경유).
- 프롬프트는 자산(`prompts/`), 비밀키 커밋 금지.
- 아키텍처는 임의 변경하지 않는다 — 필요하면 ADR 제안.

→ 다음: [repository-tour.md](repository-tour.md)
