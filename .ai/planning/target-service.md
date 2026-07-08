# Target Service — 24시간 상시 "회사 뇌" (북극성)

> 오너 정의(2026-07-08). DIP 가 "완성 + 24시간 구동" 되었을 때의 최종 상태.
> 이 문서는 목표(To-Be)다. 현재 상태는 하단 "현재 위치" 표 참조. 관련: [ADR-009], [ADR-010], [knowledge-library](knowledge-library.md).

## 한 줄 정의
**수집(주기) → 지식화(이벤트) → 제공(Pull+Push) → 되먹임** 네 루프가 사람 개입 없이 돌고,
`api·worker·scheduler·infra` 가 상시 떠 있는 상태. 비용은 "새 이슈 위키화 + 질문 답변"에만 붙고 나머지(수집·임베딩·검색)는 상시 무료.

## 상시 구동 구성요소
| 구성요소 | 진입점 | 24시간 | 하는 일 |
|---|---|---|---|
| 인프라 (Postgres+pgvector, Redis, Neo4j) | docker | ✅ | 데이터·벡터 저장, 이벤트 큐 |
| API | `apps.api` | ✅ | 질문 받기(`/ask`) + Jira 웹훅 |
| Worker | `apps.worker` | ✅ | 이벤트 소비 → 위키 생성·임베딩 |
| Scheduler | `apps.scheduler` | ✅ | 주기 Jira/Git 동기화 |
| MCP 서버 | `apps.mcp` | 접속 시 | Claude Desktop 검색 |

> 상시 서비스 → 개인 PC 아닌 **서버**에 올린다.

## 네 개의 루프

### 🔄 루프 1 — 수집 (주기, Scheduler) · LLM 0
```
[매 N분] scheduler → Jira/Git 동기화 → 새 이슈/변경 수집
   → PII·시크릿 스크러빙(수집 시점, 기존 f7903b5) → issues 저장
   → 이벤트 발행: IssueCreated / IssueUpdated
```

### 🔄 루프 2 — 지식화 (이벤트, Worker) · 💰 이슈당 1회(멱등)
```
IssueCreated ─▶ Worker 구독
   → Context 조립(이슈 + 검증지식 grounding)  [Context Before AI]
   → LLM 위키 생성(wiki_service) → 로컬 임베딩(무료) → pgvector 저장
```

### 🔄 루프 3 — 제공 (두 방향)
Pull (사람이 물어봄) · 💰 질문당 소액:
```
질문 ─▶ API /ask (또는 MCP·Slack) → 질문 임베딩 → pgvector top-k(R)
   → 검색 근거만 프롬프트 → LLM 답변(G) → 출처 인용 반환
```
Push (시스템이 밀어줌, 팀 격차 해소) · 검색만이면 LLM 0:
```
IssueCreated ─▶ 유사 과거 위키 top-k(전 팀) 검색
   → "3개월 전 결제팀이 같은 걸 겪음: [링크]" → 이슈에 자동 첨부
```

### 🔁 되먹임 — 뇌가 스스로 큰다
```
/ask 가 "근거 못 찾음" ─▶ gap 로그 기록 → "자주 묻는데 답 못하는 것"
   → 다음에 무엇을 수집·위키화할지 신호 → 루프1·2로 환류
```

## "맞는" 상태 체크리스트 (완성 정의)
- [ ] 새 이슈 → 자동으로 위키 생성·검색됨 (루프1→2 자동, 사람 개입 0)
- [ ] 질문 → 출처와 함께 답, 없으면 "모른다" (루프3 Pull)
- [ ] 이슈 생성 → 관련 과거 지식 자동 첨부 (루프3 Push)
- [ ] 못 답한 질문이 쌓여 지식 구멍이 드러남 (되먹임)
- [ ] 임베딩·검색 상시 무료, LLM 비용은 "새 이슈 위키화 + 질문 답변"에만

## 현재 위치 (2026-07-08 갱신 — 4루프 배선 완료)
| 루프 | 지금 상태 |
|---|---|
| 1. 수집 | 🟢 스케줄러 배선(`apps/scheduler/run`, 주기 루프→Redis 발행). 기본 OFF(`SCHEDULER_ENABLED=false`, APR-002 승인 대기) |
| 2. 지식화 | 🟢 이벤트 자동화(`WikiAutoGenerator` + `apps/worker/run`) — IssueCreated→자동 위키·임베딩 |
| 3-Pull | 🟢 `POST /ask` API + gap 로그, MCP `search_wiki` |
| 3-Push | 🟢 `RelatedKnowledgePush`(유사 위키 내부 연결). 실 Jira 코멘트 **쓰기는 게이트**(미구현) |
| 되먹임 | 🟡 gap 로그(`query_gaps`) 적재됨 — "무엇을 위키화할지" 자동 우선순위화는 후속 |
| 브로커 | 🟢 `RedisEventBus`(ADR-011, Streams+group) — scheduler↔worker 프로세스 분리 구동 |
> 4루프 backbone 이 실 Redis 왕복으로 e2e 검증됨. 남은 건: 실 자동수집 활성화(APR-002), Push의 실 Jira 쓰기 승인, 되먹임 활용.

## 승인/설계 게이트
- **Redis 기반 이벤트 브로커** — 현 EventBus 는 in-process(InMemory). 다중 프로세스(scheduler↔worker) 상시 구동엔 Redis 백엔드 필요 → 신규 ADR.
- **APR-002** — 실 Jira 접근·PII(수집 거버넌스). 주기 자동수집 착수 게이트.
- **Push의 Jira 쓰기** — 이슈에 자동 코멘트 = Jira **쓰기** 권한(현재 읽기 전용). 별도 승인. 초기엔 내부 저장(관련링크)로 시작, 실 코멘트는 승인 후.
- **접근제어** — [ADR-010]/[APR-010] 팀별 서가 격리.

## 권장 구현 순서 (얇은 슬라이스부터)
1. **루프2 이벤트 자동화**(in-process) — IssueCreated → 자동 위키 생성·임베딩. 거버넌스 리스크 0. ← *첫 벽돌*
2. **루프3-Pull API** — `POST /ask`(RAG) + gap 로그(되먹임 씨앗).
3. **루프3-Push**(내부 저장판) — IssueCreated → 유사 위키 top-k 를 이슈에 "관련지식"으로 연결.
4. **Redis 이벤트 브로커** → scheduler·worker 분리 상시 구동.
5. **주기 수집 스케줄러**(APR-002) + Push 실 Jira 코멘트(쓰기 승인).
