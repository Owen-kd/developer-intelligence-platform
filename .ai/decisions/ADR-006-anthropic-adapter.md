# ADR-006 — 실 LLM 어댑터로 Anthropic SDK 채택

- 상태: Accepted
- 날짜: 2026-07-07
- 관련: [APR-003](../planning/approvals/APR-003-dependencies.md) · [APR-005](../planning/approvals/APR-005-llm-vendor-data.md) · [Sprint-14](../tasks/Sprint-14.md) · [ADR-003](ADR-003-eventbus.md)

## 맥락
Sprint-14 는 fake 어댑터를 실 어댑터로 교체한다. Agent(Triage/Impact)가 실제 추론을 하려면
`LLMClient` 포트(infrastructure/llm) 뒤에 실 벤더 어댑터가 필요하다. 벤더 기본값·데이터 정책은
[APR-005]에서 **Anthropic / `claude-opus-4-8` / Context의 Knowledge만 전송**으로 승인됐다.

## 결정
`infrastructure/anthropic/client.py` 에 **`AnthropicClient(LLMClient)`** 를 추가하고,
런타임 의존성 **`anthropic` SDK**([APR-003] 승인분)를 `pyproject.toml` 에 하한 명시로 추가한다.
모델 호출은 `AsyncAnthropic().messages.create(...)` 로 하고, 응답의 text 블록만 반환한다.

## 근거
- 공식 SDK → 인증/재시도/스트리밍/타입이 견고. raw HTTP 대비 유지보수 부담↓.
- 포트-어댑터 유지 → OpenAI 등으로 교체 시 상위 코드 불변. 기본값만 바뀐다.
- 비동기(`AsyncAnthropic`) → 프로젝트의 async I/O 원칙과 정합.

## 절충 / 리스크
- 벤더 SDK 의존 추가(공급망) → infrastructure 계층에 격리, 포트로 교체 가능성 유지.
- 외부 데이터 전송/비용 → [APR-005] 정책 준수: Knowledge 기반 Context만 전송, `max_tokens` 상한.
- 모델 출력 신뢰 금지 → 출력 검증은 상위 Agent(스키마/파싱, 실패 시 폴백) 책임 유지.

## 결과
- `shared/config/settings.py`: `anthropic_api_key` / `anthropic_model` / `llm_max_tokens` 추가.
- 시크릿은 `.env`(gitignore), `.env.example` 만 커밋. 운영은 시크릿 매니저.
- 조립 루트에서 `FakeLLMClient` → `AnthropicClient` 로 스왑(키가 있을 때). 상위 로직 변경 0.
- 후속: 벤더 데이터-보존/학습 옵트아웃 확인, PII/비밀 스크러빙 정식화([APR-005] 후속 과제).
