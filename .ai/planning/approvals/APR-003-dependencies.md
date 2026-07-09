# APR-003 — 신규 런타임 의존성 배치 승인

- 상태: **Approved (부분)** — 소유자 승인 2026-07-07 (Sprint-14 착수분: `anthropic`, `httpx`). 나머지(neo4j 등)는 해당 Sprint에서 재확인.
- 요청일: 2026-07-07
- 요청자: Project Planner (AI)
- 관련 Sprint: Sprint-03, 04, 07, 08, 14
- 관련 ADR: 각 승인 시 ADR-006~ 생성 (Sprint-14: [ADR-006](../../decisions/ADR-006-anthropic-adapter.md))

## 요청 요약
[coding-guidelines]: "근거 없이 새 의존성 추가 금지 → 추가 시 ADR". 로드맵 완주에 필요한 의존성을 **배치로 사전 승인**하고, 채택 시 개별 ADR을 남긴다.

## 왜 사람이 결정해야 하나
- 의존성은 공급망/보안/유지보수 부담. 벤더 락인 가능성.

## 후보 의존성
| Sprint | 목적 | 후보 | 비고 |
|--------|------|------|------|
| 03 | Jira 클라이언트 | `atlassian-python-api` 또는 직접 httpx | httpx 직접이면 신규 의존성 없음 |
| 04 | Git 히스토리 | `GitPython` 또는 `git` CLI 호출 | CLI 래핑이면 의존성 최소 |
| 07 | 그래프 | `neo4j`(공식 driver) | 사실상 필수 |
| 07 | 임베딩/벡터 | `pgvector`+`sentence-transformers` 또는 외부 임베딩 API | [APR-004]와 연동 |
| 08 | LLM | `openai`, `anthropic` SDK | infrastructure 계층에서만 |

## 선택지
1. **(추천)** "표준 라이브러리/httpx 우선, 불가피할 때만 SDK 추가" 원칙 승인 + 위 표를 상한으로.
2. 개별 Sprint마다 ADR로 단건 승인.
3. 특정 항목 제외(직접 호출 강제).

## 영향
- 승인 시: Sprint-03/04/07/08이 막힘 없이 진행, 채택분만 `pyproject.toml`에 하한 명시 + ADR.
- 미승인 시: 해당 Sprint 착수 불가.

## 승인 체크
- [x] 승인 (Sprint-14 착수분: `anthropic` SDK + `httpx`. 원칙: 표준/httpx 우선, LLM은 벤더 SDK 허용) — 소유자, 2026-07-07
- [ ] 조건부 승인 (조건: __________)
- [ ] 거부 / 보류
- 비고: neo4j / 임베딩(APR-004) 등 나머지 후보는 각 Sprint 착수 시 재확인.
