"""Git 도메인 엔티티 + 이슈 키 파싱."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Jira 이슈 키 패턴: PROJ-123 (대문자 시작 프로젝트 키 - 숫자)
# 앞이 영숫자면 더 큰 토큰의 일부이므로 제외(`XPA20-1` 방지), 단 `_`·`/` 등 구분자 뒤는 허용.
# 실 브랜치/머지 메시지의 `.../kaya_m_PA20-19827` 형태를 잡기 위함.
_ISSUE_KEY_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z][A-Z0-9]+-\d+")


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
