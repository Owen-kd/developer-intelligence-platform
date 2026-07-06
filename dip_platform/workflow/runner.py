"""WorkflowRunner — Agent 실행을 오케스트레이션하고 각 step 을 감사한다."""

from __future__ import annotations

import uuid

from dip_platform.audit import AuditLog
from dip_platform.context import Context
from shared.logger import get_logger

from .agent import Agent, AgentResult

_logger = get_logger("workflow.runner")


class WorkflowRunner:
    """Agent 를 실행하며 입력/출력을 audit 에 남긴다."""

    def __init__(self, audit: AuditLog) -> None:
        self._audit = audit

    async def execute(
        self, agent: Agent, context: Context, correlation_id: str | None = None
    ) -> AgentResult:
        cid = correlation_id or str(uuid.uuid4())
        await self._audit.record(
            "agent.step.start",
            {"agent": agent.name, "task": context.task, "target": context.target},
            cid,
        )
        result = await agent.run(context)
        await self._audit.record(
            "agent.step.result",
            {"agent": agent.name, "kind": result.kind, "confidence": result.confidence},
            cid,
        )
        _logger.info(
            "workflow.executed",
            agent=agent.name,
            target=context.target,
            kind=result.kind,
            correlation_id=cid,
        )
        return result
