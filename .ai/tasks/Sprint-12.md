# Sprint-12 — Auth + Audit 완성

- 상태: Todo
- Phase / Milestone: Phase 4 (Product & Ops) / M4
- 의존성: **Sprint-11** (노출 표면 존재), Sprint-08 (audit 최소 도입분)
- 병렬: Sprint-13

## 문제 (Discovery)
리포트가 외부로 노출되기 시작하면 **권한(auth)** 과 **감사(audit)** 를 일원화해야 한다([../architecture/api-design.md]).
Sprint-08에서 도입한 최소 audit을 정식 계층으로 승격한다.

## 범위
- 하는 것:
  - `platform/auth`: 인증/권한 인터페이스 + API 의존성(`dependencies/`)·미들웨어 연결.
  - `platform/audit`: 이벤트/Agent step/API 접근 감사 일원화(구조화 로깅, correlation id).
  - 실패 핸들러·권한 위반 감사 경로.
- 안 하는 것(Non-goals):
  - 외부 IdP 통합 전체(최소 경로), 세밀한 RBAC 정책 전면(기본 역할만).

## 성공 기준 (DoD)
- [ ] 보호된 라우트가 인증 없이는 거부(401/403)된다.
- [ ] 이벤트 실패·Agent step·API 접근이 audit에 correlation id와 함께 남는다([../architecture/event-flow.md]).
- [ ] 인증/감사가 라우터/모듈에 흩어지지 않고 platform으로 일원화된다.
- [ ] ruff/mypy/pytest 통과.

## 설계 메모 (Design)
- 인증/권한은 `platform/auth`, 감사는 `platform/audit`로 단일화([../architecture/api-design.md]).
- 감사 스키마는 Sprint-08 최소본과 호환 유지(파괴적 변경 금지).

## Approval Gate — 착수 전
- **[APR-009]** 인증 모델/역할 범위(내부 도구 vs 멀티테넌트) 확정 (Pending).

## 체크리스트
- [ ] 구현 (auth → dependencies/middleware → audit 일원화)
- [ ] 권한/감사 테스트
- [ ] 리뷰
- [ ] `state` 갱신

## 회고
- 잘된 것:
- 개선할 것:
