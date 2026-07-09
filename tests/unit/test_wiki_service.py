"""위키 생성 서비스 + 임베더 단위 테스트 (외부 모델/DB 없이 결정적) — ADR-009."""

from __future__ import annotations

import json

from dip_platform.registry import FilePromptRegistry
from infrastructure.embedding.client import FakeEmbedder
from infrastructure.llm.client import FakeLLMClient
from modules.knowledge.application.wiki_service import (
    WIKI_TYPE,
    WikiGenerationService,
    wiki_embedding_text,
)
from modules.knowledge.domain.entity import IssueSnapshot, Knowledge
from modules.knowledge.domain.repository import KnowledgeRepository


class _FakeRepo(KnowledgeRepository):
    def __init__(self) -> None:
        self.saved: dict[str, Knowledge] = {}

    async def save(self, knowledge: Knowledge) -> None:
        self.saved[knowledge.id] = knowledge

    async def list_by_issue(self, issue_id: str) -> list[Knowledge]:
        return [k for k in self.saved.values() if k.issue_id == issue_id]

    async def get(self, knowledge_id: str) -> Knowledge | None:
        return self.saved.get(knowledge_id)


def _wiki_json(_system: str, _user: str) -> str:
    return json.dumps(
        {
            "title": "쿠팡 옵션 수정여부 버그",
            "symptom": "수정안함인데 옵션이 수정됨",
            "root_cause": "compareOpt 비교 로직 결함",
            "resolution": "옵션 수정여부 플래그 확인",
            "code_refs": "online.ts:compareOpt, ol_shop_opt",
            "related_issues": ["ENG-8404"],
            "content": "## 처리 흐름\n...\n## 근본원인\ncompareOpt",
        },
        ensure_ascii=False,
    )


def _snapshot() -> IssueSnapshot:
    return IssueSnapshot(
        issue_id="i-1",
        jira_key="PA20-19864",
        summary="[쿠팡] 상품옵션 수정여부 수정안함 > 수정됨",
        status="진행 중",
        priority="Highest",
        comments=(),
        commit_shas=(),
        source_event_ids=(),
        components=("상품-오류-엔진", "쿠팡"),
    )


async def test_generate_builds_wiki_knowledge() -> None:
    repo = _FakeRepo()
    service = WikiGenerationService(
        FakeLLMClient(responder=_wiki_json), FilePromptRegistry(), repo
    )

    wiki = await service.generate(_snapshot())

    assert wiki.type == WIKI_TYPE
    assert wiki.issue_id == "i-1"
    assert wiki.summary == "쿠팡 옵션 수정여부 버그"
    assert wiki.body["root_cause"] == "compareOpt 비교 로직 결함"
    assert "issue:PA20-19864" in wiki.sources
    # 결정적 id → 재생성 시 같은 행 upsert
    assert repo.saved[wiki.id] is wiki


async def test_generate_is_idempotent_id() -> None:
    repo = _FakeRepo()
    service = WikiGenerationService(
        FakeLLMClient(responder=_wiki_json), FilePromptRegistry(), repo
    )
    first = await service.generate(_snapshot())
    second = await service.generate(_snapshot())
    assert first.id == second.id
    assert len(repo.saved) == 1


def test_wiki_embedding_text_includes_key_fields() -> None:
    knowledge = Knowledge(
        id="k-1",
        type=WIKI_TYPE,
        issue_id="i-1",
        summary="제목",
        body={"symptom": "증상X", "root_cause": "원인Y", "content": "본문Z"},
        sources=("issue:PA20-1",),
    )
    text = wiki_embedding_text(knowledge)
    assert "제목" in text and "증상X" in text and "원인Y" in text and "본문Z" in text


async def test_fake_embedder_is_deterministic_and_sized() -> None:
    embedder = FakeEmbedder(dim=16)
    assert embedder.dim == 16
    one = await embedder.embed_query("쿠팡 옵션")
    two = await embedder.embed_query("쿠팡 옵션")
    assert one == two
    assert len(one) == 16
    docs = await embedder.embed_documents(["a", "b"])
    assert len(docs) == 2 and len(docs[0]) == 16
