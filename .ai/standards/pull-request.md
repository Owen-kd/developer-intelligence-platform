# Standard — Pull Request

## 목적
변경을 리뷰 가능한 단위로 제안하고, 병합 전에 검증한다.

## 크기
- 작게 유지한다. 리뷰 가능한 범위(대략 한 가지 목적).
- 거대한 PR은 논리 단위로 분할한다.

## 제목 · 본문
- 제목: 커밋 규약과 동일 형식 — `feat(jira): add issue collector`.
- 본문 포함 항목:
  - **무엇을 / 왜** (문제와 해결)
  - 관련 이슈/태스크 링크 (`.ai/tasks/`)
  - 스크린샷/로그(해당 시)
  - 체크리스트(아래)

## 머지 전 체크리스트
- [ ] 품질 게이트 통과: `ruff` · `mypy` · `pytest`
- [ ] 워크플로우 준수: Discovery→Design→Implementation→Review→Release
- [ ] 아키텍처 일관성: 의존성 방향, 외부호출 infrastructure 경유, 모듈 직접 import 없음
- [ ] Sprint 범위만 구현(추측성 추상화·미래 기능·placeholder TODO 없음)
- [ ] 문서 갱신: `current-task.md`, 필요 시 ADR
- [ ] 비밀키 없음

## 리뷰
- 구현자와 리뷰어를 분리한다(예: 다른 AI/사람).
- 리뷰 기준·기록: [review.md](review.md), [../workflow/04-review.md](../workflow/04-review.md), [../templates/review.md](../templates/review.md).

## 관련
- [branch.md](branch.md) · [commit.md](commit.md) · [testing.md](testing.md)
