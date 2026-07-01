# Project Overview

## DIP — Developer Intelligence Platform

### 한 줄 정의
Jira · Git · Codebase · Incident 데이터를 하나의 **AI Context**로 엮어, 개발 조직의 반복 판단(분류·영향도·리뷰·릴리즈)을 자동화하는 플랫폼.

### 해결하려는 문제
- 이슈가 들어오면 사람이 매번 "이게 어디에 영향 있지?"를 수동으로 추적한다.
- Jira 코멘트, Git 히스토리, 코드, DB 스키마가 흩어져 있어 맥락 조립에 시간이 든다.
- 그 조립된 맥락이 사람 머릿속에만 있고 재사용되지 않는다.

### 핵심 가치 흐름
```
Issue → Comment → Git → DB → Context → (LLM Agent) → 판단/보고서
```

### 주요 유스케이스
1. **Triage** — 새 이슈를 자동 분류/우선순위화.
2. **Impact Analysis** — 이슈/변경의 코드·API·DB 영향도 산출.
3. **Review** — 코드 변경 리뷰 보조.
4. **Incident Analysis** — 장애 발생 시 관련 맥락 자동 수집·정리.
5. **Release** — 릴리즈 준비/판단 보조.

### 설계 철학
처음부터 MSA로 가지 않는다. 그러나 **언제든 서비스로 분리 가능한 Modular Monolith**로 만든다.
자세한 원칙: [../core/architecture-principles.md](../core/architecture-principles.md)

### 관련 문서
- 기술 스택: [tech-stack.md](tech-stack.md)
- 로드맵: [../planning/roadmap.md](../planning/roadmap.md)
- 현재 작업: [current-task.md](current-task.md)
