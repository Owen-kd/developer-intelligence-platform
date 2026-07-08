"""Knowledge 도메인 — 재사용 가능·출처 추적 가능한 지식 자산.

계약: [.ai/contracts/knowledge-contract.md]
- 모든 Knowledge 는 출처(sources)를 가진다.
- Promotion 은 append 지향(파괴 금지).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class IssueSnapshot:
    """Promotion 입력 — 한 이슈의 정제 전 원천 모음(읽기 포트가 제공).

    `source_event_ids` 로 출처(Event)를 보존한다.
    """

    issue_id: str
    jira_key: str
    summary: str
    status: str
    priority: str
    comments: tuple[str, ...]
    commit_shas: tuple[str, ...]
    source_event_ids: tuple[str, ...]
    assignee: str = ""  # 담당자(enrich: "누가")
    reporter: str = ""  # 문의자
    description: str = ""  # 본문(원천, 2차 LLM 요약용)
    labels: tuple[str, ...] = ()  # 도메인 태그
    components: tuple[str, ...] = ()  # 도메인 서가


@dataclass(frozen=True)
class Knowledge:
    """정제된 지식 항목. AI 가 소비하는 유일한 지식 자산이다."""

    id: str
    type: str
    issue_id: str
    summary: str
    body: dict[str, object]
    sources: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = "derived"  # 신뢰등급: 'verified'(전문가) / 'derived'(자동)
