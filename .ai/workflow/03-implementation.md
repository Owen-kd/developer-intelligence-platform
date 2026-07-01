# 03 — Implementation (구현)

> 목적: 설계를 작고 검증 가능한 단위로 코드로 옮긴다.

## 입력
- 설계 노트

## AI가 할 일
1. **작게 쪼갠다** — 도메인 → application → infrastructure → presentation 순으로, 각 단계 동작 확인.
2. **규칙 준수** — [../core/coding-guidelines.md] · [../core/naming-conventions.md].
   - 타입 힌트, async I/O, 외부호출은 infrastructure, 프롬프트는 파일에서.
3. **테스트 동반** — 새 로직에 unit 테스트. 외부 시스템은 목킹.
4. **관측성** — 로깅(`shared/logger`), 필요 시 감사 이벤트.
5. **자체 점검** — `ruff check` / `mypy` / `pytest` 를 돌린다.

## 산출물
- 동작하는 코드 + 테스트.
- 갱신된 [../context/current-task.md].

## 게이트
- [ ] `ruff` / `mypy` / `pytest` 통과(또는 실패를 정직히 보고).
- [ ] 설계에서 벗어난 점은 문서/ADR에 반영.
- [ ] 비밀키·프롬프트 하드코딩 없음.
- [ ] 커밋이 작고 논리적 단위로 나뉨.

→ 통과하면 [04-review.md](04-review.md).
