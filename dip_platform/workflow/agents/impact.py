"""Impact Agent + 파이프라인.

그래프 근거(영향 커밋)를 KnowledgeItem 으로 Context 에 주입해 Agent 가 소비하게 한다
(원천 직접 소비 금지, 출처=graph 보존). 영향 커밋 목록은 그래프에서 산출한 사실을 쓴다.
"""

from __future__ import annotations

from dataclasses import replace

from dip_platform.context import Context, ContextBuilder, KnowledgeItem
from dip_platform.event import Event, EventBus
from dip_platform.registry import PromptRegistry
from dip_platform.workflow.agent import Agent, AgentResult
from dip_platform.workflow.events import IMPACT_ANALYZED, ImpactAnalyzedPayload
from dip_platform.workflow.ports import ImpactEvidenceSource
from dip_platform.workflow.runner import WorkflowRunner
from dip_platform.workflow.validation import parse_json_output
from infrastructure.llm.client import LLMClient
from shared.exceptions import ValidationError
from shared.logger import get_logger

_logger = get_logger("workflow.impact")

_PROMPT = "impact/analyze"
_REQUIRED = ("summary", "confidence")


def _render_context(context: Context) -> str:
    if not context.knowledge:
        return "관련 Knowledge 없음."
    return "다음 근거로 영향도를 요약하라:\n" + "\n".join(
        f"- {item.summary} (출처: {', '.join(item.sources)})" for item in context.knowledge
    )


class ImpactAgent(Agent):
    """Context+그래프근거로 영향도를 요약한다."""

    name = "impact-agent"

    def __init__(self, llm: LLMClient, registry: PromptRegistry) -> None:
        self._llm = llm
        self._registry = registry

    async def run(self, context: Context) -> AgentResult:
        system = self._registry.get(_PROMPT)
        raw = await self._llm.complete(system, _render_context(context))

        parsed = parse_json_output(raw, required=_REQUIRED)
        try:
            confidence = float(parsed["confidence"])  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"confidence 가 실수가 아니다: {exc}") from exc

        summary = str(parsed["summary"])
        return AgentResult(
            kind="impact",
            output={"summary": summary},
            confidence=confidence,
            rationale=summary,
        )


def _fallback() -> AgentResult:
    return AgentResult(
        kind="impact",
        output={"summary": "영향도 분석 실패 — 저확신 폴백"},
        confidence=0.0,
        rationale="LLM 출력 검증 실패",
    )


class ImpactPipeline:
    """Context 조립(+그래프 근거) → Agent 실행 → ImpactAnalyzed 발행."""

    def __init__(
        self,
        builder: ContextBuilder,
        runner: WorkflowRunner,
        agent: ImpactAgent,
        evidence: ImpactEvidenceSource,
        bus: EventBus,
    ) -> None:
        self._builder = builder
        self._runner = runner
        self._agent = agent
        self._evidence = evidence
        self._bus = bus

    async def run(self, issue_id: str) -> AgentResult:
        base = await self._builder.build("impact", issue_id)
        shas = await self._evidence.impacted_commit_shas(issue_id)

        context = base
        if shas:
            evidence_item = KnowledgeItem(
                knowledge_id="graph:impact",
                summary=f"그래프상 영향 커밋: {', '.join(shas)}",
                sources=("graph",),
            )
            context = replace(
                base,
                knowledge=(*base.knowledge, evidence_item),
                sources=(*base.sources, "graph"),
            )

        try:
            result = await self._runner.execute(self._agent, context)
        except ValidationError:
            _logger.warning("impact.fallback", issue_id=issue_id)
            result = _fallback()

        await self._bus.publish(
            Event(
                IMPACT_ANALYZED,
                ImpactAnalyzedPayload(
                    issue_id=issue_id,
                    summary=str(result.output["summary"]),
                    impacted_shas=tuple(shas),
                    confidence=result.confidence,
                ),
            )
        )
        return result
