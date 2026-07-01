# ADR-002 — 웹 프레임워크로 FastAPI 채택

- 상태: Accepted
- 날짜: 2026-07-01
- 관련: [ADR-001](ADR-001-python.md)

## 맥락
API 진입점이 필요하다: 헬스체크, 리포트 조회, 분석 트리거, 그리고 향후 웹훅(Jira 등) 수신.
비동기 I/O(DB, LLM, 외부 API)가 지배적이다.

## 결정
**FastAPI + Pydantic v2 + Uvicorn** 을 채택한다.

## 근거
- 네이티브 async/await → LLM·DB·외부 호출 동시성에 적합.
- Pydantic v2 기반 검증/직렬화가 도메인 DTO와 자연스럽게 맞물림.
- OpenAPI 문서 자동 생성 → 내부 협업/디버깅 이점.
- 의존성 주입(Depends)으로 세션/인증 컨텍스트 주입이 깔끔.

## 절충 / 리스크
- 프레임워크 종속 → 라우터는 얇게 유지하고 로직을 `modules/service` 로 위임해 완화.
- 무거운 CPU 작업은 API가 아니라 `apps/worker` 로 분리.

## 결과
- 진입점 `apps/api/main.py`, 구조 `routers/middlewares/dependencies`.
- `/health` 는 의존성 상태 포함, DB 다운 시 200+degraded.
- 세부: [../architecture/api-design.md](../architecture/api-design.md)
