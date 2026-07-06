# ADR-005 — `platform/` 패키지를 `dip_platform/` 로 리네임

- 상태: Accepted
- 날짜: 2026-07-07
- 관련: [../architecture/folder-structure.md] · [../architecture/system-overview.md] · [ADR-003](ADR-003-eventbus.md)

## 맥락
최상위 Python 패키지 `platform/` 이 **표준 라이브러리 `platform` 모듈과 이름이 충돌**한다.
저장소 루트가 `sys.path` 에 오르면(앱/테스트 실행의 일반적 상황) `import platform` 이 프로젝트 패키지로 해석되어,
stdlib `platform` 을 쓰는 모든 의존성(SQLAlchemy, mypy, uvicorn/click 등)이 `AttributeError: module 'platform' has no attribute 'python_implementation'` 로 깨진다.
반대로 stdlib 가 이기면 프로젝트의 `from platform.event import ...` 가 깨진다. **두 이름은 공존할 수 없다.**
(실측: `import platform` → `.../platform/__init__.py`, `python_implementation` 없음. mypy/pytest 수집 실패 재현됨.)

## 결정
아키텍처의 **"platform 레이어" 개념은 유지**하고, Python **패키지 디렉터리만 `platform/` → `dip_platform/`** 로 리네임한다.

## 근거
- stdlib 충돌은 우회 불가능하다(src-layout도 이름 충돌은 못 고침).
- 레이어 이름을 바꾸지 않으므로 아키텍처/의존성 방향/모듈 경계는 그대로다(import 이름만 변경).
- 대안(모든 stdlib-platform 의존성 회피)은 비현실적.

## 절충 / 리스크
- `.ai` 문서/태스크의 코드 경로 표기(`platform/…`, `from platform.…`)는 `dip_platform` 을 가리키도록 읽는다(개념어 "platform 레이어"는 산문에서 유지).
- import 경로: `from dip_platform.event import EventBus` 형태.

## 결과
- `pyproject.toml` `packages` 목록: `platform` → `dip_platform`.
- `git mv platform dip_platform` (히스토리 보존).
- 품질 게이트 복구: ruff/mypy(strict, 92 files)/pytest 통과 확인.
- 이후 모든 `platform/*`(event/context/workflow/registry/auth/audit) 구현은 `dip_platform/*` 에 위치.
