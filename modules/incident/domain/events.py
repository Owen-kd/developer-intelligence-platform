"""Incident 도메인 이벤트 페이로드."""

from __future__ import annotations

from dataclasses import dataclass

from dip_platform.event import EventPayload

INCIDENT_PROMOTED = "IncidentPromoted"


@dataclass(frozen=True)
class IncidentPromotedPayload(EventPayload):
    """Knowledge 가 Incident 로 승격되었다."""

    incident_id: str
    issue_id: str
