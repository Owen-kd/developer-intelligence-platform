"""Jira 도메인 엔티티 — 저장·전파의 기준 형태."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Comment:
    """이슈 코멘트 도메인 엔티티."""

    external_id: str
    author: str
    body: str
    created_at: str


@dataclass
class Issue:
    """이슈 도메인 엔티티.

    `id` 는 영속화 후 부여되는 저장소 식별자다(수집 시점엔 None).
    """

    jira_key: str
    type: str
    status: str
    priority: str
    summary: str
    created_at: str
    updated_at: str
    assignee: str = ""
    reporter: str = ""
    description: str = ""
    labels: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    id: str | None = None
