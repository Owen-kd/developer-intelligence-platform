# Review-002 — 지식위키 RAG + 24시간 4루프 자동화 (PR #2)

- 대상: 브랜치 `feature/sprint-14-real-llm-postgres` (main 대비 20커밋), [PR #2](https://github.com/Owen-kd/developer-intelligence-platform/pull/2)
- 날짜: 2026-07-09
- 구현: Claude(이 세션). **리뷰어는 분리 필요**(04-review 원칙) — 이 문서는 리뷰 진입용 맵.

## 무엇을 만들었나
사용자 비전 "AI DevOps Platform"(덱)의 첫 실전 구현. 이슈 → LLM 위키 → 로컬 임베딩 → pgvector →
RAG, 그리고 수집→지식화→제공(Pull/Push)→되먹임 4루프를 이벤트로 자동화. 상세: [target-service](../planning/target-service.md).

## 결정 기록(ADR)
- [ADR-009](../decisions/ADR-009-local-embedding-pgvector.md) 로컬 임베딩(fastembed)+pgvector
- [ADR-010](../decisions/ADR-010-team-shelf-access-control.md) 팀별 서가 접근제어(1단계 구현, 기본 OFF)
- [ADR-011](../decisions/ADR-011-redis-event-bus.md) Redis Streams EventBus

## 리뷰 체크포인트
### 정확성
- LLM 출력은 `parse_json_output` 로 검증, 배치는 이슈별 실패 격리(전체 중단 없음).
- gap 임계 0.82 는 e5 코사인 분포 라이브 관측 보정치(무관 ~0.79 / 관련 ~0.88+).
- 정제는 **비파괴**(원본 코멘트 미변경, clean view 만) — 헌법 "Never overwrite history" 준수.

### 아키텍처
- 의존성 방향 준수: 외부(임베딩/Redis/LLM/Jira)는 infrastructure 어댑터 뒤. 포트-어댑터.
- 이벤트 자동화: InMemory(단일프로세스)·Redis(다중프로세스) 둘 다 같은 `EventBus` 포트.
- 접근제어: 단일 서가 필터를 read 경로(/ask·MCP search_wiki/search_issues/get_issue)에 시행.

### 품질/검증
- ruff ✅ · mypy strict(208 files) ✅ · pytest(85) ✅
- 라이브 스모크: pgvector RAG(PA20-19864 0.90) · Redis 왕복 · 전체 e2e · 접근제어 격리 · 정제 실측 · 되먹임 후보(ENG-8404) · Docker 빌드+구동
- 유닛 신규: wiki/auto/push/ask-gap/gap-analysis/refinement/access-policy/scheduler

## 게이트(승인 필요 — 코드는 OFF 기본)
| 항목 | 스위치 | 게이트 |
|------|--------|--------|
| 실 자동수집 | `SCHEDULER_ENABLED=true` | APR-002 |
| 팀 격리 | `ACCESS_CONTROL_ENABLED=true` | APR-010 |
| Push 실 Jira 코멘트 | (미구현) | Jira 쓰기 승인 |

## 알려진 한계 / 후속
- Push는 내부 저장만(실 Jira 코멘트 아님). 되먹임 후보매칭은 키워드 기반(의미검색 정밀화 후속).
- 접근제어: `get_expert_knowledge`·이슈 API(인메모리) 미적용, 실 인증(OIDC) 미구현.
- 위키는 상품 도메인 30건만 실생성(405/ENG 전량은 비용 결정 대기).
- MCP per-user 신원은 프로세스 env(DIP_TEAM) 기반(로컬 신뢰) — 민감 서가는 분리 검토.
