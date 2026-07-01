# API Design

## 프레임워크
FastAPI + Pydantic v2. 진입점 `apps/api/main.py`.
결정 배경: [../decisions/ADR-002-fastapi.md](../decisions/ADR-002-fastapi.md)

## 구성
```
apps/api/
├── main.py          # 앱 부트스트랩 + lifespan
├── routers/         # 리소스별 라우터 (issues, impact, ...)
├── middlewares/     # 로깅/인증/에러 핸들링
└── dependencies/    # FastAPI Depends (세션, 인증 컨텍스트 등)
```
- 라우터는 얇게. 비즈니스 로직은 `modules/<x>/application/service.py` 로 위임한다.
- 요청/응답 모델은 각 모듈 `presentation/dto.py` 또는 라우터 옆에 둔다.

## 규약
- 경로: 복수형 명사 kebab — `/issues`, `/impact-analyses`.
- 시스템: `/health`(liveness+의존성), 추후 `/ready`, `/version`.
- 상태코드: 생성 201, 검증오류 422(Pydantic), 도메인 오류는 4xx로 매핑.
- 에러 응답 형식 통일: `{ "error": { "code", "message", "detail" } }`.
- 버저닝: 필요 시 `/v1` 프리픽스.

## /health 계약 (현재 구현)
```json
{
  "status": "ok | degraded",
  "env": "local",
  "version": "0.1.0",
  "dependencies": { "postgres": "up | down" }
}
```
- 의존성(DB)이 죽어도 200 + `degraded` 를 반환한다(라이브니스와 레디니스 구분).

## 규칙
- 라우터에서 외부 시스템 직접 호출 금지 → service → infrastructure.
- 인증/권한은 `platform/auth`, 감사 로깅은 `platform/audit` 로 일원화.
