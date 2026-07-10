"""Obsidian 볼트 export — Postgres 위키를 마크다운 볼트로 내보낸다(비파괴).

Postgres 가 진실원천. 이 스크립트는 파생 뷰(사람이 읽고/편집 가능한 Obsidian 볼트)를 만든다.
관련 이슈(issue_related_wiki + body.related_issues)는 `[[JIRA-KEY]]` 링크로 이어져
Obsidian 그래프 뷰에서 지식망이 그대로 보인다. 위키 편집→verified 승격 되먹임은 후속.

조립 계층(apps): 저장소(read)에서 데이터를 받아 순수 포매터(modules presentation)로 문자열을
만들고 파일로 쓴다. 포매팅 로직 자체는 `modules/knowledge/presentation/obsidian.py`(순수).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from modules.knowledge.infrastructure.repository import PostgresKnowledgeRepository
from modules.knowledge.presentation.obsidian import (
    index_markdown,
    to_markdown,
    vault_filename,
)
from shared.logger import get_logger

_logger = get_logger("obsidian.export")


@dataclass
class ExportResult:
    out_dir: str
    written: int  # 쓴 위키 노트 수
    skipped: int  # jira_key 없어 건너뛴 수(파일명 불안정 방지)


async def export_vault(out_dir: str) -> ExportResult:
    """모든 위키를 out_dir 아래 `<JIRA-KEY>.md` + `index.md`(홈 MOC) 로 내보낸다."""
    repo = PostgresKnowledgeRepository()
    wikis = await repo.list_wikis_with_meta()
    related_by_issue = await repo.related_wiki_keys_by_issue()

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    index_entries: list[tuple[str, str, tuple[str, ...]]] = []
    for knowledge, jira_key, components in wikis:
        if not jira_key:
            skipped += 1  # 파일명/링크 안정성을 위해 Jira 키 없는 위키는 건너뛴다
            continue
        related_keys = related_by_issue.get(knowledge.issue_id, [])
        markdown = to_markdown(
            knowledge,
            jira_key=jira_key,
            related_keys=related_keys,
            components=components,
        )
        (out / vault_filename(jira_key)).write_text(markdown, encoding="utf-8")
        index_entries.append((jira_key, knowledge.summary, components))
        written += 1

    (out / "index.md").write_text(index_markdown(index_entries), encoding="utf-8")
    _logger.info("obsidian.exported", written=written, skipped=skipped, out_dir=str(out))
    return ExportResult(out_dir=str(out), written=written, skipped=skipped)
