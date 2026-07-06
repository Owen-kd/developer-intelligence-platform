"""Git 클라이언트 (포트 + 어댑터). 외부(저장소 히스토리) 접근은 이 계층에만.

`FakeGitClient` 는 fixture 커밋을 반환한다. 실제 연동은 같은 포트로 `LocalGitClient`
(예: `git log` 래핑)를 추가하면 된다([APR-003]).
"""

from __future__ import annotations

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
