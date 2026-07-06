"""실 PA20 이슈(Postgres) → 실 Anthropic LLM 분류 → 실제 토큰/비용 출력.

사용:
    python -m apps.cli.triage_real [건수]
"""

from __future__ import annotations

import asyncio
import sys

from dip_platform.audit import InMemoryAuditLog
from dip_platform.context import ContextBuilder
from dip_platform.event import InMemoryEventBus, InMemoryEventStore
from dip_platform.registry import FilePromptRegistry
from dip_platform.workflow import WorkflowRunner
from dip_platform.workflow.agents.triage import TriageAgent, TriagePipeline
from infrastructure.anthropic.client import AnthropicClient
from infrastructure.postgres import connection as pg
from modules.jira.infrastructure.repository import PostgresIssueRepository
from modules.knowledge.application.service import PromotionService
from modules.knowledge.infrastructure.context_source import KnowledgeRepositorySource
from modules.knowledge.infrastructure.repository import (
    InMemoryKnowledgeRepository,
    PostgresIssueSourceReader,
)

_KRW = 1350.0  # 대략 환율(USD→KRW)


async def main(limit: int) -> None:
    issues = (await PostgresIssueRepository().list_issues())[:limit]

    store = InMemoryEventStore()
    bus = InMemoryEventBus(store=store)
    knowledge_repo = InMemoryKnowledgeRepository()
    promotion = PromotionService(PostgresIssueSourceReader(), knowledge_repo, bus)

    llm = AnthropicClient()
    builder = ContextBuilder(KnowledgeRepositorySource(knowledge_repo))
    runner = WorkflowRunner(InMemoryAuditLog())
    pipeline = TriagePipeline(builder, runner, TriageAgent(llm, FilePromptRegistry()), bus)

    print(f"=== 모델: {llm.model} / 대상 {len(issues)}건 ===")
    total_in = total_out = 0
    total_cost = 0.0
    for issue in issues:
        assert issue.id is not None
        await promotion.promote_issue(issue.id)  # 원천 → Knowledge
        result = await pipeline.run(issue.id)  # 실 LLM 분류

        total_in += llm.last_input_tokens
        total_out += llm.last_output_tokens
        total_cost += llm.last_cost_usd()
        print(f"\n[{issue.jira_key}] {issue.summary[:46]}")
        print(f"   분류 → {result.output}  확신도={result.confidence}")
        print(f"   근거 → {result.rationale[:80]}")
        print(
            f"   토큰 in={llm.last_input_tokens} out={llm.last_output_tokens} "
            f"비용≈${llm.last_cost_usd():.5f} (≈{llm.last_cost_usd() * _KRW:.2f}원)"
        )

    per_issue = total_cost * _KRW / max(1, len(issues))
    print("\n=== 합계 ===")
    print(f"토큰 in={total_in} out={total_out}")
    print(f"비용≈${total_cost:.5f} (≈{total_cost * _KRW:.2f}원), 건당≈{per_issue:.2f}원")
    await pg.dispose()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 2))
