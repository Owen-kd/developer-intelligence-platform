# Approval Requests (APR)

> Project Planner가 자동 생성한 **사람 승인 대기** 목록. AI는 이 결정을 **대신 내리지 않는다**([../../core/system.md]).
> 아키텍처 변경/외부 데이터/자격증명/신규 의존성/조직 경계 결정은 사람이 승인한다.
> 승인되면 상태를 갱신하고, 필요 시 `.ai/decisions/ADR-NNN-*.md` 로 확정한다.

| APR | 제목 | Gate | 막는 Sprint | 상태 |
|-----|------|------|-------------|------|
| [APR-001](APR-001-adr004-knowledge-only.md) | ADR-004 "AI는 Knowledge만 소비" 승격 | G3 | Sprint-05 | Pending |
| [APR-002](APR-002-jira-access-pii.md) | Jira 접근·자격증명·PII 정책 | G1 | Sprint-03 | Pending |
| [APR-003](APR-003-dependencies.md) | 신규 런타임 의존성 배치 | G2 | 03·07·08 | Pending |
| [APR-004](APR-004-vector-store.md) | Vector store 선택(pgvector vs 외부) | G5 | Sprint-07 | Pending |
| [APR-005](APR-005-llm-vendor-data.md) | LLM 벤더 기본값·외부 전송 데이터 정책 | G6 | Sprint-08 | Pending |
| [APR-006](APR-006-audit-early.md) | `platform/audit` 조기 도입 | G4 | Sprint-08 | Pending |
| [APR-007](APR-007-eventbus-broker.md) | EventBus 브로커 전환 시점 | G7 | (스케일 시) | Pending |
| [APR-008](APR-008-msa-separation.md) | MSA 분리 결정 | G8 | Sprint-13 | Pending |
| [APR-009](APR-009-auth-model.md) | 인증 모델/역할 범위 | — | Sprint-12 | Pending |

## 승인 절차
1. 해당 APR을 읽고 선택지 중 하나에 체크(또는 조건부).
2. 결정이 아키텍처/불변 규칙에 해당하면 ADR로 승격.
3. Gate가 걸린 Sprint는 승인 전 착수 금지.
