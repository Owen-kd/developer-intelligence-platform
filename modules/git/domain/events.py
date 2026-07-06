"""Git 도메인 이벤트 페이로드."""

from __future__ import annotations

from dataclasses import dataclass

from dip_platform.event import EventPayload

COMMITS_LINKED = "CommitsLinked"


@dataclass(frozen=True)
class CommitsLinkedPayload(EventPayload):
    """커밋이 이슈에 링크되었다."""

    issue_id: str
    jira_key: str
    commit_id: str
    sha: str
