# APR-005 — LLM 벤더 기본값 · 외부 전송 데이터 정책

- 상태: **Approved** — 소유자 승인 2026-07-07. 기본 벤더 **Anthropic**(`claude-opus-4-8`), 전송 허용 = Context에 담긴 Knowledge 한정(원천 데이터 직접 전송 금지 유지), 비용 가드 = `max_tokens` 상한. 데이터 보존은 벤더 기본(향후 옵트아웃 확인 과제).
- 요청일: 2026-07-07
- 요청자: Project Planner (AI)
- 관련 Sprint: Sprint-08 (LLM 인프라), Sprint-09/10 (Agent), Sprint-14 (실 어댑터)
- 관련 ADR: [ADR-006](../../decisions/ADR-006-anthropic-adapter.md)

## 요청 요약
① Agent 실행의 **기본 LLM 벤더**(OpenAI vs Anthropic)와 ② **어떤 데이터를 외부 LLM으로 전송해도 되는지**의 정책을 확정한다.

## 왜 사람이 결정해야 하나
- Context가 외부 LLM으로 나간다 → 데이터 유출/규정 준수/비용 문제. AI가 임의 결정 불가.
- system.md: "Context Before AI", 원천 데이터를 LLM에 직접 보내지 않는다(Knowledge/Context 경유).

## 결정 필요 항목
1. **기본 벤더**: OpenAI / Anthropic (인프라는 둘 다 어댑터로 지원, 기본값만).
2. **전송 허용 범위**: Context에 담긴 Knowledge까지 허용? PII/비밀 필터링 규칙?
3. **비용 가드**: 토큰 예산 상한, 호출 rate/budget.
4. **데이터 보존**: 벤더의 데이터 보존/학습 사용 옵트아웃 확인.

## 선택지
1. **(추천)** 기본 Anthropic 또는 OpenAI 1개 + Context 사전 **PII/비밀 스크러빙** 필수 + 토큰 예산 상한.
2. 온프렘/로컬 모델 우선(데이터 외부 전송 최소화) — 인프라 추가 필요.
3. 보류 — Agent Sprint 전까지 결정 유예(Sprint-08 착수 불가).

## 영향
- 승인 시: Sprint-08 인프라 기본값·가드 구현, Sprint-09/10 Agent 실행 가능.
- 미승인 시: Phase 3 전체(08~10) 착수 불가.

## 승인 체크
- [x] 승인 (벤더: **Anthropic** `claude-opus-4-8`, 전송 허용: **Context의 Knowledge만**, 예산 상한: `max_tokens` 기본 1024/설정 가능) — 소유자, 2026-07-07
- [ ] 조건부 승인 (조건: __________)
- [ ] 거부 / 보류
- 후속 과제: 벤더 데이터-보존/학습 옵트아웃 확인, PII/비밀 스크러빙 규칙 정식화(현재는 Knowledge 계층이 원천 데이터 격리).
