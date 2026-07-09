# ADR-010 — 팀별 서가(component) 열람 권한 · 접근제어 모델

- 상태: **1단계 구현됨(기본 OFF)** — 코드는 머지 가능, **켜는 것(`ACCESS_CONTROL_ENABLED=true`)은 [APR-010](../planning/approvals/APR-010-access-control.md) 승인 후**
- 구현 범위(2026-07-09): `dip_platform/access`(TeamPolicy, 기본 deny) + `config/access/team_shelves.txt` + `search_semantic` 서가필터(이슈 조인) + `/ask`(헤더 `X-DIP-Team`) + **MCP 전 읽기경로**(`search_wiki`·`search_issues`·`get_issue`·`get_expert_knowledge`(미허가 차단)·`list_shelves`(허용 서가만), env `DIP_TEAM`) 시행 + 감사. 접근제어 필터 질의는 gap 로그 미오염(질문 원문 누출 방지). 라이브 격리 검증(infra/support→commerce 0건, list_shelves 팀필터). 후속: 실 인증(OIDC/JWT), 전문가 문서 서가 태깅, `/ask/gaps` 팀 스코프, 이슈 API(인메모리) 확대.
- 날짜: 2026-07-08
- 관련: [APR-010](../planning/approvals/APR-010-access-control.md) · [ADR-009](ADR-009-local-embedding-pgvector.md) · 보안/격리 논의(오너 2026-07-08)

## 맥락
지식 도서관을 "회사 뇌"로 내부 운영하려면, 아무나 모든 지식을 보게 두면 안 된다(내부정보 유출·해커 악용 대비).
오너 요구: **팀별로 볼 수 있는 권한**을 서가 단위로 설정. 다행히 이슈/지식은 이미 `components`(서가)로 태깅돼 있어 이것이 자연스러운 접근 경계다.

현재 상태의 한계:
- 인증은 `api_token` 단일(dev-token) — 사용자/팀 개념 없음.
- MCP 서버는 로컬 프로세스로 DB 를 직접 읽어 **모든** 지식을 반환(필터 없음).
- 감사(누가 무엇을 조회)는 `InMemoryAuditLog` 토대만 존재.

## 결정 (제안)
### 1. 접근 단위 = 서가(component)
- 정책: `team → 허용 서가 패턴 목록`(예: `commerce → [쿠팡, 상품-*, 주문-*]`).
- **기본 deny**: 정책이 없으면 아무것도 못 본다(안전 기본값).
- 저장: 초기엔 설정 파일/DB 테이블(`team_shelf_acl`) — 되돌리기 쉬운 형태로 시작.

### 2. 단일 시행 계층 (AccessPolicy)
- 모든 읽기 경로(MCP `search_issues`/`search_wiki`/`get_issue`/`get_expert_knowledge`, API, RAG `ask`)가
  **하나의 `AccessPolicy`** 를 거친다. 검사 로직을 분산하지 않는다(누락 방지).
- 쿼리에 `호출자 허용 서가 ∩ 행.components ≠ ∅` 필터를 추가. `get_issue` 는 반환 전 대상 이슈의 서가를 확인.
- 배치: 포트는 `dip_platform`(또는 `shared`)에 두고, 각 read 어댑터가 의존. 벡터 검색(`search_semantic`)에도 서가 필터 인자를 추가.

### 3. 신원(누가 호출하나)
- **API 경로**: 실 인증(JWT/OIDC) → 사용자 → 팀 → 정책. per-user 가 자연스러운 지점.
- **MCP 경로**: 로컬 프로세스라 per-user 어려움 → 팀별 MCP 설정에 `DIP_TEAM=<team>` 을 주입해 그 인스턴스의 팀을 고정하거나, MCP 를 인증된 API 뒤로 라우팅.

### 4. 감사
- 모든 질의를 append-only 로 기록: `(principal, 질의, 노출 서가, 결과 수, 시각)`. 이상 접근 추적.

## 단계 (한 번에 구현하지 않음)
1. **정책 + 시행 계층** — 팀→서가 매핑, 질의 필터, deny-default, 감사. 팀은 우선 설정/env 로 주입.
2. **실 인증** — API OIDC/JWT, 사용자→팀 매핑.
3. **MCP 게이트웨이** — MCP 를 인증 경유로.

## 근거
- 서가는 이미 존재하는 도메인 경계 → 새 분류체계 없이 접근제어 부착 가능.
- 단일 시행 계층 → 경로가 늘어도 정책 한 곳에서 관리, 검사 누락 리스크 최소화.
- 단계적 도입 → 1단계(필터+감사)만으로도 "전원이 전체 열람" 상태를 즉시 개선.

## 절충 / 리스크
- MCP per-user 신원은 근본적으로 약함(로컬 신뢰) → 민감 서가는 MCP 미노출/전용 인스턴스로 분리 검토.
- 서가 태깅이 누락된 지식은 정책 사각지대 → deny-default + "미분류=비공개" 규칙으로 방어.
- LLM(Anthropic)에는 여전히 context 가 나감 → 서가 필터로 "볼 수 있는 것만" context 에 넣어야(RAG 조립 시 시행). PII 스크러빙(기존)과 병행.
- 성능: 서가 필터는 `components` jsonb 조회 → 필요 시 인덱스/비정규화.

## 결과 (승인 시)
- `AccessPolicy` 포트 + 정책 저장(설정/DB) + 각 read 경로 배선.
- `search_semantic` 등 쿼리에 서가 필터 인자 추가.
- 감사 로그 영속화.
- 미승인 시: 착수 불가(현행 유지). 보안 정책 결정이라 [APR-010] 오너 승인이 게이트.
