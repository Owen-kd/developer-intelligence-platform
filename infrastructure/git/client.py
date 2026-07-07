"""Git 클라이언트 (포트 + 어댑터). 외부(저장소 히스토리) 접근은 이 계층에만.

`FakeGitClient` 는 fixture 커밋을 반환한다. 실제 연동은 같은 포트로 `LocalGitClient`
(예: `git log` 래핑)를 추가하면 된다([APR-003]).
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GitCommit:
    """Git 커밋 원천 DTO."""

    sha: str
    author: str
    message: str
    committed_at: str  # ISO-8601


class GitClient(ABC):
    """Git 읽기 전용 포트."""

    @abstractmethod
    async def fetch_commits(self) -> list[GitCommit]:
        """수집 대상 커밋을 가져온다."""


_SAMPLE_COMMITS: tuple[GitCommit, ...] = (
    GitCommit(
        sha="a1b2c3d",
        author="minsu",
        message="DIP-1 커넥션 풀 사이즈 상향으로 결제 타임아웃 해소",
        committed_at="2026-07-02T09:45:00+00:00",
    ),
    GitCommit(
        sha="e4f5a6b",
        author="jieun",
        message="chore: 로깅 포맷 정리 (관련 이슈 없음)",
        committed_at="2026-07-03T08:00:00+00:00",
    ),
)


class FakeGitClient(GitClient):
    """fixture 기반 Git 어댑터."""

    def __init__(self, commits: list[GitCommit] | None = None) -> None:
        self._commits = list(commits) if commits is not None else list(_SAMPLE_COMMITS)

    async def fetch_commits(self) -> list[GitCommit]:
        return list(self._commits)


# git log 파싱 구분자(메시지에 나올 일이 없는 제어문자): 필드=US(0x1f), 레코드=RS(0x1e)
_FIELD = "\x1f"
_RECORD = "\x1e"


def parse_git_log(raw: str) -> list[GitCommit]:
    """`git log --pretty=format:%H<US>%an<US>%cI<US>%B<RS>` 출력을 파싱한다."""
    commits: list[GitCommit] = []
    for record in raw.split(_RECORD):
        record = record.strip("\n")
        if not record.strip():
            continue
        parts = record.split(_FIELD)
        if len(parts) < 4:
            continue
        sha, author, committed_at, message = parts[0], parts[1], parts[2], parts[3]
        commits.append(
            GitCommit(
                sha=sha.strip(),
                author=author.strip(),
                message=message.strip(),
                committed_at=committed_at.strip(),
            )
        )
    return commits


class LocalGitClient(GitClient):
    """로컬 저장소 `git log` 를 파싱하는 읽기 전용 어댑터([APR-003], [ADR-008]).

    수집은 bounded(최근 N 커밋). 커밋 메시지의 이슈키는 상위 GitService 가 파싱·링크한다.
    """

    _FMT = f"%H{_FIELD}%an{_FIELD}%cI{_FIELD}%B{_RECORD}"

    def __init__(self, repo_path: str, max_commits: int = 2000) -> None:
        if not repo_path:
            raise ValueError("git_repo_path 가 비어 있습니다 (.env GIT_REPO_PATH).")
        self._repo = repo_path
        self._max = max_commits

    async def fetch_commits(self) -> list[GitCommit]:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", self._repo, "log", f"-n{self._max}", f"--pretty=format:{self._FMT}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            detail = err.decode("utf-8", errors="replace")[:200]
            raise RuntimeError(f"git log 실패({self._repo}): {detail}")
        return parse_git_log(out.decode("utf-8", errors="replace"))


class MultiRepoGitClient(GitClient):
    """여러 저장소의 커밋을 합쳐 반환한다(프론트/백엔드/워커 등 멀티 repo)."""

    def __init__(self, clients: list[GitClient]) -> None:
        if not clients:
            raise ValueError("최소 하나의 Git 클라이언트가 필요합니다.")
        self._clients = clients

    async def fetch_commits(self) -> list[GitCommit]:
        collected: list[GitCommit] = []
        for client in self._clients:
            collected.extend(await client.fetch_commits())
        return collected
