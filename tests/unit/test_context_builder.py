"""Context Builder 단위 테스트 — 재현성/토큰예산/출처보존."""

from __future__ import annotations

from dip_platform.context import Context, ContextBuilder, KnowledgeItem, KnowledgeSource


class _StubSource(KnowledgeSource):
    def __init__(self, items: list[KnowledgeItem]) -> None:
        self._items = items

    async def fetch(self, task: str, target_id: str) -> list[KnowledgeItem]:
        return list(self._items)


def _items() -> list[KnowledgeItem]:
    return [
        KnowledgeItem("k-3", "세 번째 지식", ("evt-c",)),
        KnowledgeItem("k-1", "첫 번째 지식", ("evt-a",)),
        KnowledgeItem("k-2", "두 번째 지식", ("evt-b", "evt-a")),
    ]


async def test_build_is_deterministic() -> None:
    builder = ContextBuilder(_StubSource(_items()))

    first = await builder.build("triage", "i-1")
    second = await builder.build("triage", "i-1")

    assert first == second
    # 안정 정렬: knowledge_id 오름차순
    assert [item.knowledge_id for item in first.knowledge] == ["k-1", "k-2", "k-3"]


async def test_sources_are_deduped_and_preserved() -> None:
    builder = ContextBuilder(_StubSource(_items()))

    context = await builder.build("triage", "i-1")

    assert context.sources == ("evt-a", "evt-b", "evt-c")


async def test_token_budget_truncates() -> None:
    long_items = [KnowledgeItem(f"k-{i}", "x" * 400, (f"e-{i}",)) for i in range(10)]
    builder = ContextBuilder(_StubSource(long_items), token_budget=150)

    context = await builder.build("triage", "i-1")

    assert isinstance(context, Context)
    assert context.budget_meta.items_included < context.budget_meta.items_considered
    assert context.budget_meta.tokens_used <= context.budget_meta.token_budget
    assert context.budget_meta.items_included >= 1  # 최소 1개는 담는다
