"""영향도 분석 리포트 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.api.dependencies.auth import require_principal
from apps.api.dependencies.container import get_container
from apps.composition import DipInMemoryApp

router = APIRouter(
    prefix="/impact-analyses",
    tags=["impact"],
    dependencies=[Depends(require_principal)],
)

Container = Annotated[DipInMemoryApp, Depends(get_container)]


class ImpactAnalysis(BaseModel):
    knowledge_id: str
    issue_id: str
    summary: str
    sources: list[str]


@router.get("", response_model=list[ImpactAnalysis])
async def list_impact_analyses(container: Container) -> list[ImpactAnalysis]:
    items = await container.knowledge_repo.list_by_type("impact")
    return [
        ImpactAnalysis(
            knowledge_id=item.id,
            issue_id=item.issue_id,
            summary=item.summary,
            sources=list(item.sources),
        )
        for item in items
    ]
