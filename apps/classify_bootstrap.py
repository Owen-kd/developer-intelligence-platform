"""Facet 분류 부트스트랩 — 규칙 분류기로 전 이슈를 분류·적재한다(LLM 0). [ADR-015] 1단계.

조립 계층(apps): jira 저장소에서 원시 이슈를 읽어 knowledge 의 순수 분류기로 facet 을 만들고
issue_facets 에 upsert 한다. 규칙으로 못 채운 축은 `미상`/`공통` 으로 남아 후속 LLM 보강 대상.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from modules.jira.infrastructure.repository import PostgresIssueRepository
from modules.knowledge.application.classification import (
    COMMON,
    UNKNOWN,
    Facets,
    classify_rule,
)
from shared.logger import get_logger

_logger = get_logger("classify.bootstrap")

_UNFILLED = {UNKNOWN, COMMON}


@dataclass
class BootstrapResult:
    total: int
    classified: int
    filled: dict[str, int]  # 축별 규칙으로 채운 건수(미상/공통 제외)


async def classify_all() -> BootstrapResult:
    """전 이슈를 규칙 분류해 issue_facets 에 적재하고 축별 커버리지를 반환한다."""
    repo = PostgresIssueRepository()
    rows = await repo.iter_for_classification()

    filled = {field: 0 for field in Facets.__dataclass_fields__}
    classified = 0
    for issue_id, jira_key, summary, components, labels in rows:
        facets = classify_rule(components, labels, jira_key, summary)
        await repo.save_facets(issue_id, asdict(facets), method="rule")
        classified += 1
        for field, value in asdict(facets).items():
            if value not in _UNFILLED:
                filled[field] += 1

    _logger.info("classify.bootstrap.done", total=len(rows), classified=classified)
    return BootstrapResult(total=len(rows), classified=classified, filled=filled)
