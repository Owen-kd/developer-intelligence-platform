"""AuditLog — 이벤트 실패/Agent step/접근을 기록하는 감사 포트.

각 Agent step 의 입력/출력을 남긴다([.ai/contracts/agent-contract.md]).
correlation id 로 하나의 실행을 추적할 수 있게 한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class AuditEntry:
    """감사 항목 하나."""

    action: str
    data: dict[str, object]
    correlation_id: str | None = None
    at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AuditLog(ABC):
    """감사 기록 포트."""

    @abstractmethod
    async def record(
        self, action: str, data: dict[str, object], correlation_id: str | None = None
    ) -> None:
        """감사 항목을 남긴다."""


class InMemoryAuditLog(AuditLog):
    """프로세스 메모리 기반 감사 로그(테스트/데모)."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    async def record(
        self, action: str, data: dict[str, object], correlation_id: str | None = None
    ) -> None:
        self._entries.append(AuditEntry(action=action, data=data, correlation_id=correlation_id))

    @property
    def entries(self) -> list[AuditEntry]:
        """기록된 감사 항목."""
        return list(self._entries)
