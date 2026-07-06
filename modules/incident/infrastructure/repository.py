"""IncidentRepository 인메모리 구현."""

from __future__ import annotations

from modules.incident.domain.entity import Incident
from modules.incident.domain.repository import IncidentRepository


class InMemoryIncidentRepository(IncidentRepository):
    """프로세스 메모리 기반 Incident Library."""

    def __init__(self) -> None:
        self._items: list[Incident] = []

    async def save(self, incident: Incident) -> None:
        self._items.append(incident)

    async def list_all(self) -> list[Incident]:
        return list(self._items)
