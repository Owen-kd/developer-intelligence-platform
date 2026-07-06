"""Incident Library 리포트 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.api.dependencies.auth import require_principal
from apps.api.dependencies.container import get_container
from apps.composition import DipInMemoryApp

router = APIRouter(
    prefix="/incidents",
    tags=["incidents"],
    dependencies=[Depends(require_principal)],
)

Container = Annotated[DipInMemoryApp, Depends(get_container)]


class IncidentView(BaseModel):
    id: str
    issue_id: str
    root_cause: str
    resolution: str
    prevention: str
    sources: list[str]


@router.get("", response_model=list[IncidentView])
async def list_incidents(container: Container) -> list[IncidentView]:
    incidents = await container.incident_repo.list_all()
    return [
        IncidentView(
            id=incident.id,
            issue_id=incident.issue_id,
            root_cause=incident.root_cause,
            resolution=incident.resolution,
            prevention=incident.prevention,
            sources=list(incident.sources),
        )
        for incident in incidents
    ]
