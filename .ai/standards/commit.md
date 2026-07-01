# Standard — Commit

## 형식 (Conventional Commits)
```
<type>(<scope>): <subject>

<body (선택)>
```
- `type`: `feat` `fix` `docs` `chore` `refactor` `test` `perf`.
- `scope`: 모듈/영역 — `jira`, `api`, `event`, `.ai` 등.
- `subject`: 명령형·현재형, 소문자 시작, 마침표 없음.

예:
```
feat(jira): add issue collector via infrastructure
docs(.ai): add contracts and philosophy layers
fix(api): return degraded status when postgres is down
```

## 원칙
- **작고 논리적인 단위**로 커밋한다. 한 커밋에 포맷팅 + 로직 변경을 섞지 않는다.
- 커밋은 "무엇을/왜"를 담는다. 큰 변경은 body에 이유를 적는다.
- 커밋 전 품질 게이트 통과: `ruff check .` · `mypy .` · `pytest -q`.

## 금지
- 비밀키/`.env` 커밋 금지(`.env.example` 만).
- 생성물/캐시(`.venv`, `*.egg-info`, `__pycache__`) 커밋 금지 — `.gitignore` 확인.
- "wip", "fix" 같은 의미 없는 메시지 지양.

## 관련
- [branch.md](branch.md) · [pull-request.md](pull-request.md)
