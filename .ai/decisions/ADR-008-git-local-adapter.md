# ADR-008 — 실 Git 수집 어댑터(로컬 git log)

- 상태: Accepted
- 날짜: 2026-07-07
- 관련: [APR-003](../planning/approvals/APR-003-dependencies.md) · [Sprint-14](../tasks/Sprint-14.md) · [ADR-007](ADR-007-jira-http-adapter.md)

## 맥락
Sprint-14 ③ 은 `FakeGitClient` 를 실 어댑터로 교체한다. 대상 repo(`gmp.openapi.2023`)는
로컬에 클론돼 있고(16k+ 커밋), 커밋/머지 메시지에 이슈키가 `.../kaya_m_PA20-19827` 형태로 들어있다.

## 결정
`infrastructure/git/client.py` 에 **`LocalGitClient(GitClient)`** 추가 — 로컬 `git log` 를 파싱.
- 형식: `git log -n<max> --pretty=format:%H<US>%an<US>%cI<US>%B<RS>` (제어문자 구분자).
- 읽기 전용, bounded(최근 N 커밋, 기본 2000). 외부 SDK/의존성 추가 없음(git 바이너리 사용).
- 이슈키 정규식 수정: `\b[A-Z][A-Z0-9]+-\d+\b` → `(?<![A-Za-z0-9])[A-Z][A-Z0-9]+-\d+`
  (앞이 `_`·`/` 등 구분자여도 매칭 — 실 브랜치명 형태 대응).

## 근거
- 로컬 `git log` = 토큰/외부 접근 불필요, 오프라인, 가장 빠른 실연동(Jira HTTP와 대비되는 최소경로).
- 포트(`GitClient.fetch_commits`) 뒤 교체 → GitService/모듈 코드 변경 0.
- 이슈↔커밋 링크는 `PostgresCommitRepository.resolve_issue`(issues 테이블 조회)로 성립 → 증분에도 동작.

## 절충 / 리스크
- 로컬 clone 최신화(fetch/pull)는 사용자 책임 — 어댑터는 현재 로컬 히스토리만 본다.
- provider API(PR 링크/리뷰어 등)는 미포함 — 후속(원격 어댑터)에서. 지금은 커밋 메시지의 PR 번호만 존재.
- bounded 수집 → 전량/증분 커밋 커서는 후속.

## 결과
- `shared/config/settings.py`: `git_repo_path` / `git_max_commits` + `git_configured`.
- `apps/composition_pg.collect_and_refine`: git 수집·링크를 jira 뒤에 배선(설정 있으면 실, 없으면 Fake).
- 시크릿 없음(로컬 경로). `.env.example` 에 `GIT_REPO_PATH` 추가.
