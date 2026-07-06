# Review-001 — DIP 완주 구현 (Sprint-02~13)

- 날짜: 2026-07-07
- 범위: Phase 1~4 전 파이프라인 구현(수집→지식→컨텍스트→에이전트→리포트→인시던트).
- 방식: 각 Sprint 단위 구현 후 ruff/mypy(strict)/pytest 검증, 라이브 Postgres 스모크.

## 정확성
- [x] 성공 기준 충족: 이슈 1건이 수집→Event/Timeline→Knowledge→Context→분류/영향도→Incident 로 흐른다(e2e 데모).
- [x] 엣지/에러: EventBus 핸들러 격리, LLM 출력 검증 + 폴백, 멱등 upsert(재수집 무중복), 근거 없는 Incident 승격 거부.
- [x] LLM 출력 검증: `parse_json_output` + 스키마 키 검증, 실패 시 저확신 폴백.

## 아키텍처
- [x] 의존성 방향 준수: `apps → modules → platform(dip_platform) → infrastructure → shared`. 역방향 없음.
- [x] 모듈 간 직접 import 없음 — 협업은 Event(구조적 페이로드 계약) 또는 상위 조립(apps)으로.
- [x] 외부 호출은 infrastructure 뒤에(포트-어댑터). 실 벤더는 fake 와 동일 포트로 교체만 하면 됨.
- [x] platform 이 modules 를 모르게 유지: KnowledgeSource / ImpactEvidenceSource 포트를 상위 모듈이 구현.

## 품질
- [x] 타입 힌트/네이밍/async 규칙 준수. mypy strict 170 files 통과.
- [x] 테스트 39건, 결정적(외부 목/인메모리). 라이브 DB 는 별도 스모크.
- [x] 프롬프트는 `prompts/` 파일 자산(코드 인라인 0). 비밀키 커밋 없음.

## 발견/수정한 이슈
1. **패키지명 충돌(Blocking)**: 최상위 `platform` 이 stdlib 와 충돌 → `dip_platform` 리네임([ADR-005]). 승인 후 적용.
2. **run_script 다중문장**: asyncpg prepared 는 다중 SQL 불가 → 문장 분리 실행으로 수정(라이브에서 발견).
3. **timestamptz 바인딩**: 수집 타임스탬프(ISO 문자열)를 datetime 으로 변환해 바인딩.
4. **compose 바인드 마운트**: Windows 권한 오류 → 명명 볼륨으로 전환(`docker compose up` 정상화).

## 승인 게이트 (여전히 Pending — 실 외부연동 시 필요)
- APR-002(Jira), APR-003(의존성), APR-004(벡터스토어), APR-005(LLM/데이터), APR-007/008/009.
- 현재는 전부 fake/로컬 어댑터로 대체되어 파이프라인은 완결. 실 어댑터는 포트 교체 + 승인.

## 판정
- Blocking 이슈 0. 완주 목표(Phase 1~4 동작) 달성. 후속은 실 어댑터 연동(승인 기반)과 Neo4j/임베딩 실구현.
