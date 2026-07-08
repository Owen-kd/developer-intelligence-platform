"""위키 생성 서비스 — 이슈(+검증 지식) → LLM → 재사용 가능한 위키 Knowledge.

Knowledge First / Context Before AI:
- 원천(이슈 스냅샷)과 검증된 백엔드 지식을 Context 로 조립한 뒤에만 LLM 을 호출한다.
- LLM 출력은 항상 검증(parse_json_output)한다 — 실패는 호출자에게 전파(조용히 삼키지 않음).
- 결과는 이슈당 결정적 id(멱등 upsert)로 저장 → 재실행 시 중복 생성 없음.

임베딩/색인은 이 서비스의 책임이 아니다(조립 계층이 `wiki_embedding_text` 로 색인). — ADR-009.
"""

from __future__ import annotations

import uuid

from dip_platform.registry import PromptRegistry
from dip_platform.workflow.validation import parse_json_output
from infrastructure.llm.client import LLMClient
from modules.knowledge.domain.entity import IssueSnapshot, Knowledge
from modules.knowledge.domain.repository import KnowledgeRepository

WIKI_TYPE = "wiki"
_PROMPT = "knowledge/wiki"
_REQUIRED = ("title", "symptom", "root_cause", "resolution", "content")
_GROUNDING_CHARS = 1600  # 근거 문서 1건당 프롬프트에 넣는 최대 길이(프롬프트 폭주 방지)


def wiki_embedding_text(knowledge: Knowledge) -> str:
    """위키 Knowledge 에서 임베딩할 대표 텍스트를 뽑는다(제목+증상+근본원인+본문)."""
    body = knowledge.body if isinstance(knowledge.body, dict) else {}
    parts = [
        knowledge.summary,
        str(body.get("symptom", "")),
        str(body.get("root_cause", "")),
        str(body.get("content", "")),
    ]
    return "\n".join(part for part in parts if part)


class WikiGenerationService:
    """이슈 스냅샷을 위키 Knowledge 로 정제한다(LLM 1회 호출)."""

    def __init__(
        self,
        llm: LLMClient,
        registry: PromptRegistry,
        repo: KnowledgeRepository,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._repo = repo

    async def generate(
        self, snapshot: IssueSnapshot, grounding: tuple[Knowledge, ...] = ()
    ) -> Knowledge:
        system = self._registry.get(_PROMPT)
        user = _render_user(snapshot, grounding)
        raw = await self._llm.complete(system, user)
        parsed = parse_json_output(raw, required=_REQUIRED)
        knowledge = _to_knowledge(snapshot, parsed, grounding)
        await self._repo.save(knowledge)
        return knowledge


def _render_user(snapshot: IssueSnapshot, grounding: tuple[Knowledge, ...]) -> str:
    parts = [
        f"# 이슈 {snapshot.jira_key}",
        f"제목: {snapshot.summary}",
        f"상태/우선순위: {snapshot.status}/{snapshot.priority}",
        f"서가(components): {', '.join(snapshot.components) or '-'}",
        f"라벨: {', '.join(snapshot.labels) or '-'}",
        "",
        "## 본문",
        snapshot.description or "(본문 없음)",
    ]
    if snapshot.comments:
        parts.append("")
        parts.append("## 코멘트")
        parts.extend(f"- {comment}" for comment in snapshot.comments)
    if grounding:
        parts.append("")
        parts.append("## 검증된 백엔드 지식(근거)")
        for item in grounding:
            content = str(item.body.get("content", "")) if isinstance(item.body, dict) else ""
            parts.append(f"### {item.summary}")
            parts.append(content[:_GROUNDING_CHARS])
    return "\n".join(parts)


def _to_knowledge(
    snapshot: IssueSnapshot,
    parsed: dict[str, object],
    grounding: tuple[Knowledge, ...],
) -> Knowledge:
    related = parsed.get("related_issues")
    related_list = [str(x) for x in related] if isinstance(related, list) else []
    body: dict[str, object] = {
        "content": str(parsed["content"]),
        "symptom": str(parsed["symptom"]),
        "root_cause": str(parsed["root_cause"]),
        "resolution": str(parsed["resolution"]),
        "code_refs": str(parsed.get("code_refs", "")),
        "related_issues": related_list,
    }
    sources = (f"issue:{snapshot.jira_key}",) + tuple(
        source for item in grounding for source in item.sources
    )
    return Knowledge(
        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"wiki:{snapshot.jira_key}")),
        type=WIKI_TYPE,
        issue_id=snapshot.issue_id,
        summary=str(parsed["title"]),
        body=body,
        sources=sources,
        source="derived",
    )
