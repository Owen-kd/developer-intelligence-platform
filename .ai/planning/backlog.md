# Backlog

> 아직 착수하지 않은 작업 후보의 목록. 우선순위는 대략적이며, 스프린트로 당겨질 때 태스크([../tasks/])로 구체화된다.
> 이정표: [milestones.md](milestones.md)

## 규칙
- 여기 항목은 **후보**다. 추측성 구현을 미리 하지 않는다(현재 Sprint만 구현).
- 착수 시 `.ai/tasks/Sprint-NN.md` 로 옮겨 Discovery부터 시작한다.

## High (다음 후보 — M1)
- [ ] EventBus 인터페이스/in-memory 구현 (`platform/event`)
- [ ] Jira Collector (`modules/jira` + `infrastructure/jira`)
- [ ] jira_sync 스케줄러
- [ ] 초기 마이그레이션(issues/comments/events)

## Medium (M2)
- [ ] Knowledge 승격 파이프라인
- [ ] Context Builder (`platform/context`)
- [ ] Neo4j 그래프 적재
- [ ] 임베딩/검색(`modules/embedding`, `modules/search`)

## Low (M3+)
- [ ] Triage/Impact/Review Agent
- [ ] 리포트 API/UI
- [ ] 권한(`platform/auth`) / 감사(`platform/audit`)
- [ ] Incident Library 성숙

## Ideas / 미분류
- [ ] GPT·Cursor·Codex용 진입 파일(AGENTS.md, .cursor/rules) — `.ai` 재사용
- [ ] `.ai` 문서 링크 체커(CI)
