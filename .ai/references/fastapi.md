# Reference — FastAPI

> DIP에서 FastAPI를 어떻게 쓰는지에 대한 간략 참고. 채택 배경: [../decisions/ADR-002-fastapi.md](../decisions/ADR-002-fastapi.md)

## 프로젝트 내 사용
- 진입점: `apps/api/main.py` (앱 부트스트랩 + `lifespan`).
- 실행: `uvicorn apps.api.main:app --reload`.
- 버전: `fastapi>=0.110`, `uvicorn[standard]>=0.29`, Pydantic v2.

## 핵심 개념 (DIP 관점)
- **lifespan**: startup/shutdown 관리. 현재 종료 시 `infrastructure.postgres.dispose()` 호출.
- **Depends(의존성 주입)**: DB 세션·인증 컨텍스트 주입 지점. `apps/api/dependencies/`.
- **Pydantic 모델**: 요청/응답 검증·직렬화. 도메인 DTO와 연결.
- **APIRouter**: 리소스별 라우터를 `apps/api/routers/` 로 분리.

## 규약 (프로젝트)
- 라우터는 얇게 — 로직은 `modules/<x>/application/service.py` 로 위임.
- 라우터에서 외부 시스템/LLM 직접 호출 금지.
- 응답/에러 형식은 [../contracts/api-contract.md](../contracts/api-contract.md) 준수.

## 자주 쓰는 패턴
```python
from fastapi import APIRouter, Depends
router = APIRouter(prefix="/issues", tags=["issues"])

@router.get("/{issue_id}")
async def get_issue(issue_id: str, svc = Depends(get_issue_service)):
    return await svc.get(issue_id)
```

## 외부 문서
- 공식: https://fastapi.tiangolo.com/
- Pydantic v2: https://docs.pydantic.dev/
