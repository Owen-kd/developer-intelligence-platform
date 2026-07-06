"""Triage Agent + 파이프라인.

Context Before AI: Context 없이는 LLM 을 호출하지 않는다.
LLM 출력은 항상 검증하며, 실패 시 저확신 폴백으로 대체한다(파이프라인이 죽지 않는다).
"""

from __future__ import annotations

from dip_platform.context import Context, ContextBuilder
from dip_platform.event import Event, EventBus
from dip_platform.registry import PromptRegistry
from dip_platform.workflow.agent import Agent, AgentResult
from dip_platform.workflow.events import ISSUE_TRIAGED, IssueTriagedPayload
from dip_platform.workflow.runner import WorkflowRunner
from dip_platform.workflow.validation import parse_json_output
from infrastructure.llm.client import LLMClient
from shared.exceptions import ValidationError
from shared.logger import get_logger

_logger = get_logger("workflow.triage")

_PROMPT = "triage/classify"
_ALLOWED_PRIORITY = {"low", "medium", "high"}
_REQUIRED = ("category", "priority", "confidence", "rationale")


def _render_context(context: Context) -> str:
    if not context.knowledge:
        return "관련 Knowledge 없음."
    lines = [f"- {item.summary} (출처: {', '.join(item.sources)})" for item in context.knowledge]
    return "다음 Knowledge 를 근거로 분류하라:\n" + "\n".join(lines)


class TriageAgent(Agent):
    """Context+프롬프트로 이슈를 분류한다."""

    name = "triage-agent"

    def __init__(self, llm: LLMClient, registry: PromptRegistry) -> None:
        self._llm = llm
        self._registry = registry

    async def run(self, context: Context) -> AgentResult:
        system = self._registry.get(_PROMPT)
        user = _render_context(context)
        raw = await self._llm.complete(system, user)

        parsed = parse_json_output(raw, required=_REQUIRED)
        priority = str(parsed["priority"])
        if priority not in _ALLOWED_PRIORITY:
            raise ValidationError(f"허용되지 않은 priority: {priority}")
        try:
            confidence = float(parsed["confidence"])  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"confidence 가 실수가 아니다: {exc}") from exc

        return AgentResult(
            kind="triage",
            output={"category": str(parsed["category"]), "priority": priority},
            confidence=confidence,
            rationale=str(parsed["rationale"]),
        )


def _fallback() -> AgentResult:
    return AgentResult(
        kind="triage",
        output={"category": "question", "priority": "medium"},
        confidence=0.0,
        rationale="LLM 출력 검증 실패 — 저확신 폴백",
    )


class TriagePipeline:
    """Context 조립 → Agent 실행(감사) → IssueTriaged 발행."""

    def __init__(
        self,
        builder: ContextBuilder,
        runner: WorkflowRunner,
        agent: TriageAgent,
        bus: EventBus,
    ) -> None:
        self._builder = builder
        self._runner = runner
        self._agent = agent
        self._bus = bus

    async def run(self, issue_id: str) -> AgentResult:
        context = await self._builder.build("triage", issue_id)
        try:
            result = await self._runner.execute(self._agent, context)
        except ValidationError:
            _logger.warning("triage.fallback", issue_id=issue_id)
            result = _fallback()

        await self._bus.publish(
            Event(
                ISSUE_TRIAGED,
                IssueTriagedPayload(
                    issue_id=issue_id,
                    category=str(result.output["category"]),
                    priority=str(result.output["priority"]),
                    confidence=result.confidence,
                    rationale=result.rationale,
                ),
            )
        )
        return result
