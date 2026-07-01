# Contract — Module

> `modules/<x>` 하나가 지켜야 하는 계약. 이 계약을 지키면 모듈은 언제든 서비스로 분리 가능하다.

## 목적
비즈니스 능력(capability)을 자율적이고 분리 가능한 단위로 캡슐화한다.

## 책임
- 자기 도메인의 유스케이스를 소유한다(수집·변환·판단 중 해당 범위).
- DDD-lite 계층을 유지한다: `application` / `domain` / `infrastructure` / `presentation`.
- 외부 세계와의 접점은 자기 `infrastructure` 또는 최상위 `infrastructure/` 를 통한다.

## Input
- 다른 모듈이 발행한 **Event**(구독).
- `presentation` 을 통한 요청(API 라우터 → service).
- 조립된 **Context**(AI가 필요한 경우).

## Output
- 자기 도메인 변화의 **Event** 발행.
- 저장소(Repository)를 통한 영속화.
- `presentation` 을 통한 응답 DTO.

## Rules
- 의존성 방향 준수: `apps → modules → platform → infrastructure → shared`. 역방향 금지.
- **다른 모듈을 직접 import 하지 않는다.** 협업은 Event(`platform/event`)로.
- 외부 SDK(OpenAI/Jira/DB)를 모듈 안에서 직접 호출하지 않는다 → `infrastructure/`.
- 원천 데이터를 LLM에 직접 보내지 않는다 → Context Builder 경유.
- 분리 테스트: "이 폴더를 통째로 떼면 컴파일/실행되는가?"가 항상 Yes여야 한다.

## Example
```
modules/jira/
├── application/service.py      # JiraService — 유스케이스
├── domain/entity.py            # Issue (엔티티)
├── domain/repository.py        # IssueRepository (추상)
├── infrastructure/repository.py# IssueRepositoryImpl (Postgres)
└── presentation/controller.py  # 라우터 바인딩
# 협업: JiraService 가 IssueCreated 발행 → comment 모듈이 구독
```

## 관련
- [../core/architecture-principles.md](../core/architecture-principles.md) · [event-contract.md](event-contract.md)
