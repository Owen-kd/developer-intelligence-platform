# Standard — Review

> 코드/변경 리뷰의 표준. 실행 절차형 리뷰는 [../playbooks/review.md], 게이트는 [../workflow/04-review.md] 참조.

## 원칙
- **구현자 ≠ 리뷰어.** 독립 시각으로 검증한다.
- 지적에는 항상 **구체적 위치(`file:line`)와 근거**를 단다. 추측성 지적 금지.
- 취향 문제는 Nit으로 낮추고, 정확성·아키텍처는 Blocking으로 올린다.

## 리뷰 축
### 정확성
- 성공 기준 충족, 엣지케이스/에러 경로, 동시성.
- LLM 출력 검증 유무.

### 아키텍처
- 의존성 방향 준수, 모듈 직접 import 없음.
- 외부 호출 infrastructure 경유.
- 원천 데이터 직접 LLM 전달 없음(Context Builder 경유).
- 모듈 분리 가능성 유지.

### 품질
- 네이밍/스타일/타입 규칙, 테스트 충분성, 중복·복잡성.
- 비밀키/프롬프트 하드코딩 없음.

## 판정
- `Approve` / `Request changes` — 근거 명시.
- Blocking 이슈가 0이어야 머지.

## 기록
- 리뷰 노트는 [../reviews/](../reviews/) 에 `review-NNN.md`(템플릿: [../templates/review.md]).

## 관련
- [pull-request.md](pull-request.md) · [testing.md](testing.md)
