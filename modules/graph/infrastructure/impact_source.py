"""GraphService → platform ImpactEvidenceSource 어댑터.

modules→platform 의존은 허용된다. GraphService 의 영향 탐색을 워크플로 포트로 노출한다.
"""

from __future__ import annotations

from dip_platform.workflow.ports import ImpactEvidenceSource
from modules.graph.application.service import GraphService


class GraphImpactSource(ImpactEvidenceSource):
    """그래프에서 영향 커밋 sha 를 산출한다."""

    def __init__(self, graph: GraphService) -> None:
        self._graph = graph

    async def impacted_commit_shas(self, issue_id: str) -> list[str]:
        return await self._graph.impacted_commit_shas(issue_id)
