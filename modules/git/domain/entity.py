"""Git 도메인 엔티티 + 이슈 키 파싱."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Jira 이슈 키 패턴: PROJ-123 (대문자로 시작하는 프로젝트 키 - 숫자)
_ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")


@dataclass
class Commit:
    """Git 커밋 도메인 엔티티."""

    sha: str
    author: str
    message: str
    committed_at: str
    id: str | None = None


def parse_issue_keys(message: str) -> list[str]:
    """커밋 메시지에서 이슈 키를 중복 없이(등장 순서로) 추출한다."""
    seen: dict[str, None] = {}
    for match in _ISSUE_KEY_RE.findall(message):
        seen.setdefault(match, None)
    return list(seen)
