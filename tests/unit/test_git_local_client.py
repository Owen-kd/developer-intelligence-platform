"""LocalGitClient / parse_git_log / 이슈키 파싱 단위 테스트 (네트워크·실 repo 無)."""

from __future__ import annotations

import pytest

from infrastructure.git.client import (
    FakeGitClient,
    GitCommit,
    LocalGitClient,
    MultiRepoGitClient,
    parse_git_log,
)
from modules.git.domain.entity import parse_issue_keys

_US = "\x1f"
_RS = "\x1e"


def _record(sha: str, author: str, date: str, message: str) -> str:
    return f"{sha}{_US}{author}{_US}{date}{_US}{message}{_RS}"


def test_parse_git_log_multiline_messages() -> None:
    raw = (
        _record("abc123", "kaya", "2026-07-02T09:00:00+09:00", "Merge PR #1\n\nbody line")
        + "\n"
        + _record("def456", "owen", "2026-07-03T10:00:00+09:00", "fix: something")
    )
    commits = parse_git_log(raw)
    assert [c.sha for c in commits] == ["abc123", "def456"]
    assert commits[0].author == "kaya"
    assert "body line" in commits[0].message  # 멀티라인 본문 보존


def test_issue_key_parsing_real_branch_format() -> None:
    # 실 머지 커밋의 브랜치명 임베드 형태
    assert parse_issue_keys("Merge pull request #9885 from playauto/kaya_m_PA20-19827") == [
        "PA20-19827"
    ]
    assert parse_issue_keys("chore: 로깅 정리 (이슈 없음)") == []
    assert parse_issue_keys("ENG-42 and PA20-7") == ["ENG-42", "PA20-7"]


def test_missing_repo_path_raises() -> None:
    with pytest.raises(ValueError):
        LocalGitClient("")


async def test_multi_repo_concatenates_commits() -> None:
    a = FakeGitClient([GitCommit("s1", "u", "PA20-1 fix", "2026-01-01T00:00:00+00:00")])
    b = FakeGitClient([GitCommit("s2", "v", "PA20-2 feat", "2026-01-02T00:00:00+00:00")])
    multi = MultiRepoGitClient([a, b])
    commits = await multi.fetch_commits()
    assert [c.sha for c in commits] == ["s1", "s2"]


def test_multi_repo_requires_clients() -> None:
    with pytest.raises(ValueError):
        MultiRepoGitClient([])
