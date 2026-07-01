# Architecture Principles

## 1. Modular Monolith, MSA-ready
- 하나의 배포 단위지만, 각 `modules/<x>` 는 **독립 서비스로 분리 가능한 형태**를 유지한다.
- 모듈은 자기 domain/application/infrastructure/presentation 을 가진다(DDD-lite).
- 분리 기준: "이 폴더를 통째로 떼서 별도 저장소로 옮겼을 때 컴파일/실행되는가?" 를 항상 자문한다.

## 2. 의존성 방향 (한 방향)
```
apps ──▶ modules ──▶ platform ──▶ infrastructure ──▶ shared
```
- 역방향 import 금지. `shared` 는 아무도 import 하지 않는 게 정상(그 반대만).
- 모듈 A 가 모듈 B 를 **직접 import 하지 않는다.** 협업이 필요하면 EventBus(`platform/event`)나 명시적 인터페이스를 통한다.

## 3. 외부 세계는 infrastructure 뒤에
- OpenAI/Anthropic/Jira/Git/Neo4j/Postgres/Redis 호출은 전부 `infrastructure/` 에만 존재한다.
- 모듈은 인프라의 **구현이 아니라 인터페이스**에 의존한다(포트-어댑터).
- 이유: 벤더 교체(OpenAI↔Anthropic), 테스트 목킹, 서비스 분리가 쉬워진다.

## 4. Event-Driven 내부
- 모듈 간 결합을 낮추기 위해 EventBus로 통신한다.
- 예: `IssueCreated` → comment 모듈 구독 → git 모듈 구독 → context 생성.
- 동기 호출이 꼭 필요하면 명시적 서비스 인터페이스로, 이유를 남긴다.

## 5. Context is King
- DIP의 핵심 가치는 **AI Context 조립**이다: Issue → Comment → Git → DB → Context.
- 이 조립은 `platform/context` 에서 오케스트레이션한다. 데이터 수집은 각 모듈/인프라가 담당한다.

## 6. 프롬프트·지식은 코드 밖
- 프롬프트: `prompts/`, `.ai/prompts/`
- 회사/도메인 지식: `.ai/knowledge/`
- 의사결정: `.ai/decisions/` (ADR)

## 안티패턴 (하지 말 것)
- 모듈이 다른 모듈 내부 클래스를 직접 import
- `modules/` 안에서 `openai.` / `httpx.` 직접 호출
- `shared` 가 특정 모듈을 알게 되는 것
- 프롬프트 문자열을 서비스 코드에 하드코딩
