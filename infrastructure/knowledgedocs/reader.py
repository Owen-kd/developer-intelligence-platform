"""전문가 지식 문서(`knowledge/*.md`) 리더 — verified Knowledge 흡수용.

간단한 frontmatter(`--- key: value ---`) + 본문 마크다운을 읽는다.
파일당 결정적 id(파일명 기반)를 부여해 재수집 시 멱등(upsert)하게 한다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeDoc:
    doc_id: str
    title: str
    type: str
    issues: tuple[str, ...]
    code_refs: str
    content: str
    filename: str


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, parts[2].strip()


def read_docs(directory: str) -> list[KnowledgeDoc]:
    base = Path(directory)
    if not base.is_dir():
        return []
    docs: list[KnowledgeDoc] = []
    for path in sorted(base.glob("*.md")):
        meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
        issues = tuple(i.strip() for i in meta.get("issues", "").split(",") if i.strip())
        docs.append(
            KnowledgeDoc(
                doc_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"knowledgedoc:{path.name}")),
                title=meta.get("title", path.stem),
                type=meta.get("type", "expert"),
                issues=issues,
                code_refs=meta.get("code_refs", ""),
                content=body,
                filename=path.name,
            )
        )
    return docs
