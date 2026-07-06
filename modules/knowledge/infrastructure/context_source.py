"""KnowledgeRepository → platform Context 포트 어댑터.

modules→platform 의존은 허용된다. 이 어댑터가 모듈 Knowledge 를
플랫폼의 KnowledgeItem 으로 매핑해 ContextBuilder 에 공급한다.
"""

from __future__ import annotations

from dip_platform.context import KnowledgeItem, KnowledgeSource
from modules.knowledge.domain.repository import KnowledgeRepository


class KnowledgeRepositorySource(KnowledgeSource):
    """이슈 대상 Knowledge 를 조회해 KnowledgeItem 으로 변환한다."""

    def __init__(self, repo: KnowledgeRepository) -> None:
        self._repo = repo

    async def fetch(self, task: str, target_id: str) -> list[KnowledgeItem]:
        items = await self._repo.list_by_issue(target_id)
        return [
            KnowledgeItem(
                knowledge_id=item.id,
                summary=item.summary,
                sources=item.sources,
            )
            for item in items
        ]
