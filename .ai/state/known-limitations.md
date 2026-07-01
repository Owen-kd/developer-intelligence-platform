# State — Known Limitations

> 현재 알려진 한계. 결함이 아니라 "아직 여기까지"라는 정직한 경계다. 해소되면 항목을 옮기거나 지운다.

## 기능 경계
- **파이프라인 미구현**: 수집(Collector)·Event·Timeline·Knowledge·Context Builder·Agent가 아직 코드로 존재하지 않는다. 현재 실행 가능한 것은 `/health` 뿐이다.
- **외부 연동 없음**: Jira/Git/LLM 연동은 골격만. 실제 데이터가 들어오지 않는다.
- **영속 스키마 없음**: `database/migrations` 가 비어 있어 애플리케이션 테이블이 아직 없다(연결만 가능).

## 운영/환경
- **로컬 Python**: 시스템 기본이 3.9라 프로젝트 요구(3.11+)와 불일치. 현재 venv는 Homebrew `python3.14`로 생성해 우회 중.
- **비밀·자격증명 미구성**: `.env` 는 예시(`.env.example`)만 있고 실제 키(OpenAI/Anthropic/Jira)는 비어 있다.
- **staging/production 미정의**: 배포 파이프라인·시크릿 관리 미구축.

## 테스트/품질
- 테스트 커버리지 최소(헬스 스모크 1건). integration/e2e 미작성.
- CI 파이프라인 없음(품질 게이트는 로컬 수동 실행).

## 문서
- `.ai/knowledge/*`, `.ai/prompts/*` 다수가 빈 뼈대(회사 지식·프롬프트 미작성).
- `.ai` 문서 링크의 자동 검증(링크 체커) 없음.

## 관련
- [current-architecture.md](current-architecture.md) · [technical-debt.md](technical-debt.md) · [../planning/backlog.md](../planning/backlog.md)
