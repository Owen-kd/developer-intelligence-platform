# State — Technical Debt

> 의도적으로 미룬 결정/지름길과 그 이유. 부채는 "왜 졌는지"와 "언제 갚을지"를 함께 적는다.
> 한계(아직 미구현)는 [known-limitations.md](known-limitations.md), 여기는 "이미 진 빚".

| # | 부채 | 왜 졌나 | 리스크 | 갚을 시점 |
|---|------|---------|--------|-----------|
| 1 | 의존성 lock 파일 없음(하한만 명시) | 초기 속도 우선 | 재현성 저하 | 첫 배포 파이프라인 도입 시 |
| 2 | prompts 위치 이원화(`prompts/` vs `.ai/prompts/`) | 골격 단계에서 역할 미정 | 혼선 가능 | Agent 구현 시 역할 확정(운영 자산 vs AI 지침) |
| 3 | EventBus 계약만 있고 구현 없음 | Sprint 범위 밖 | 설계-구현 드리프트 | M1에서 in-memory 구현 |
| 4 | 로컬 Python 버전 불일치 우회(3.14 venv) | 시스템 3.9 제약 | 팀 환경 편차 | 표준 런타임/도구(pyenv 등) 합의 시 |
| 5 | CI 없음 — 품질 게이트 수동 | 아직 협업 초기 | 회귀 누락 | 협업자 합류/PR 도입 시 |
| 6 | `.ai` 링크 무결성 수동 확인 | 자동화 미도입 | 링크 부패 | 링크 체커(backlog) 도입 시 |

## 원칙
- 새 부채를 지면 이 표에 **이유·리스크·상환 시점**과 함께 기록한다.
- 아키텍처에 영향 주는 지름길은 부채로 남기지 말고 ADR로 결정한다.

## 관련
- [current-architecture.md](current-architecture.md) · [../decisions/](../decisions/) · [../planning/backlog.md](../planning/backlog.md)
