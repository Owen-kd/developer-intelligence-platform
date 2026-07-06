"""Sprint-08 기반 테스트 — validation / audit / runner / fake LLM."""

from __future__ import annotations

import pytest

from dip_platform.audit import InMemoryAuditLog
from dip_platform.context import BudgetMeta, Context
from dip_platform.workflow import Agent, AgentResult, WorkflowRunner, parse_json_output
from infrastructure.llm.client import FakeLLMClient
from shared.exceptions import ValidationError


def _context() -> Context:
    return Context(
        task="triage",
        target="i-1",
        knowledge=(),
        sources=(),
        budget_meta=BudgetMeta(2000, 0, 0, 0),
    )


class _EchoAgent(Agent):
    name = "echo-agent"

    async def run(self, context: Context) -> AgentResult:
        return AgentResult(
            kind="echo",
            output={"target": context.target},
            confidence=1.0,
            rationale="ok",
        )


def test_parse_json_output_ok() -> None:
    parsed = parse_json_output('{"category": "bug", "priority": "high"}', required=("category",))
    assert parsed["category"] == "bug"


def test_parse_json_output_rejects_non_json() -> None:
    with pytest.raises(ValidationError):
        parse_json_output("not json at all")


def test_parse_json_output_requires_keys() -> None:
    with pytest.raises(ValidationError):
        parse_json_output('{"a": 1}', required=("category",))


async def test_fake_llm_responder() -> None:
    client = FakeLLMClient(responder=lambda system, user: f"{system}|{user}")
    assert await client.complete("S", "U") == "S|U"


async def test_runner_executes_and_audits() -> None:
    audit = InMemoryAuditLog()
    runner = WorkflowRunner(audit)

    result = await runner.execute(_EchoAgent(), _context(), correlation_id="cid-1")

    assert result.kind == "echo"
    actions = [entry.action for entry in audit.entries]
    assert actions == ["agent.step.start", "agent.step.result"]
    assert all(entry.correlation_id == "cid-1" for entry in audit.entries)
