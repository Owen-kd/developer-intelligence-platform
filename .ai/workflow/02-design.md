# 02 — Design (설계)

> 목적: 구현 전에 "어떻게"를 정한다. 되돌리기 비싼 결정을 여기서 내린다.

## 입력
- Discovery 노트

## AI가 할 일
1. **배치 결정** — 어느 `modules/<x>` 인가, 어느 DDD 계층(application/domain/infrastructure/presentation)인가.
2. **인터페이스 스케치** — 핵심 함수/클래스 시그니처, 도메인 엔티티, 이벤트(있다면).
3. **의존성 확인** — 의존성 방향(apps→modules→platform→infrastructure→shared)을 위반하지 않는가. 외부 호출은 infrastructure로 가는가.
4. **데이터 영향** — 스키마 변경/마이그레이션 필요 여부([../architecture/database-design.md]).
5. **대안 비교** — 2개 이상 접근이 있으면 간단히 비교, 하나를 **추천**한다.
6. **결정 기록** — 아키텍처에 영향 주는 선택은 [../decisions/](../decisions/) 에 ADR로.

## 산출물
- 설계 노트: 배치 / 인터페이스 / 이벤트 / 데이터 변경 / 선택 근거.
- 필요 시 ADR, 태스크 업데이트.

## 게이트
- [ ] 의존성 방향/외부호출 격리 원칙을 지킨다.
- [ ] 모듈 분리 가능성을 깨지 않는다.
- [ ] 스키마 변경이 있으면 마이그레이션 계획이 있다.
- [ ] 프롬프트가 필요하면 `prompts/` 위치가 정해졌다.

→ 통과하면 [03-implementation.md](03-implementation.md).
