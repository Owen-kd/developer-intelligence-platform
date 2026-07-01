# Contract — API

> `apps/api` 의 HTTP 엔드포인트가 지켜야 하는 계약.

## 목적
외부/내부 클라이언트에 안정적인 인터페이스로 조회·트리거를 제공한다.

## 책임
- 요청을 검증하고 적절한 모듈 서비스로 위임한다.
- 일관된 응답/에러 형식을 보장한다.
- 라우터는 얇게 유지한다(비즈니스 로직 금지).

## Input
- HTTP 요청(경로/쿼리/바디). 바디는 Pydantic 모델로 검증.
- 인증 컨텍스트(`platform/auth`, 향후).

## Output
- Pydantic 응답 모델(JSON).
- 상태코드: 조회 200, 생성 201, 검증오류 422, 도메인 오류 4xx.
- 통일 에러 형식: `{ "error": { "code", "message", "detail" } }`.

## Rules
- 경로: 복수형 명사 kebab — `/issues`, `/impact-analyses`. 시스템: `/health`.
- 라우터에서 외부 시스템/LLM 직접 호출 금지 → service → infrastructure.
- 로직은 `modules/<x>/application/service.py` 로 위임.
- 호환성 파괴 변경은 버저닝(`/v1`)으로 관리.
- 인증/권한은 `platform/auth`, 감사는 `platform/audit` 로 일원화.

## Example — /health (현재 구현)
```json
{
  "status": "ok | degraded",
  "env": "local",
  "version": "0.1.0",
  "dependencies": { "postgres": "up | down" }
}
```
의존성(DB)이 죽어도 200 + `degraded` (liveness와 readiness 구분).

## 관련
- [../architecture/api-design.md](../architecture/api-design.md) · [../decisions/ADR-002-fastapi.md](../decisions/ADR-002-fastapi.md)
