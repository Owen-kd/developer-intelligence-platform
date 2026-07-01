# Sprint-01 — Foundation

- 상태: In Progress
- 목표: 실행 가능한 골격 + AI 개발 체계(.ai) 확립 (Roadmap Phase 0)

## 완료
- [x] 저장소 폴더 골격 (apps/modules/platform/infrastructure/shared/…)
- [x] pyproject / .gitignore / .env.example
- [x] docker-compose (postgres/neo4j/redis)
- [x] shared/config.settings (중앙 설정)
- [x] infrastructure/postgres.connection (async 연결 + ping)
- [x] FastAPI 부트스트랩 + `/health`
- [x] health 스모크 테스트 (pytest 통과)
- [x] `.ai/` 핵심 문서: core / context / architecture / decisions(ADR 1~3) / workflow(01~05) / playbooks / templates

## 다음 (Sprint-02 후보 → Phase 1 Ingestion)
- [ ] `platform/event` EventBus 인터페이스 + in-memory 구현
- [ ] `modules/jira` domain/application 골격 (엔티티, 리포지토리 추상)
- [ ] `infrastructure/jira` 클라이언트 (읽기 전용 수집)
- [ ] `apps/scheduler/jira_sync.py` 주기 동기화 스텁
- [ ] `database/migrations/001_init.sql` (issues, comments)

## 회고 (스프린트 종료 시 작성)
- 잘된 것:
- 개선할 것:
