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
    vault_path,
)
from shared.logger import get_logger

_logger = get_logger("obsidian.export")


@dataclass
class ExportResult:
    out_dir: str
    written: int  # 쓴 위키 노트 수
    skipped: int  # jira_key 없어 건너뛴 수(파일명 불안정 방지)


def _clean_generated(out: Path) -> None:
    """기존 생성물(.md)과 빈 폴더를 지운다 — 파생 뷰라 재조직 시 잔여물 방지(.obsidian 보존)."""
    for md in out.rglob("*.md"):
        if ".obsidian" not in md.parts:
            md.unlink()
    for path in sorted(out.rglob("*"), reverse=True):  # 깊은 곳부터 빈 폴더 제거
        if path.is_dir() and ".obsidian" not in path.parts and not any(path.iterdir()):
            path.rmdir()


async def export_vault(out_dir: str) -> ExportResult:
    """모든 위키를 out_dir 아래 `<JIRA-KEY>.md` + `index.md`(홈 MOC) 로 내보낸다."""
    repo = PostgresKnowledgeRepository()
    wikis = await repo.list_wikis_with_meta()
    related_by_issue = await repo.related_wiki_keys_by_issue()

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _clean_generated(out)  # 파생 뷰 — 기존 생성물 정리 후 재작성(idempotent, .obsidian 보존)

    written = 0
    skipped = 0
    index_entries: list[tuple[str, str, dict[str, str]]] = []
    for knowledge, jira_key, components, facets in wikis:
        if not jira_key:
            skipped += 1  # 파일명/링크 안정성을 위해 Jira 키 없는 위키는 건너뛴다
            continue
        related_keys = related_by_issue.get(knowledge.issue_id, [])
        markdown = to_markdown(
            knowledge,
            jira_key=jira_key,
            related_keys=related_keys,
            components=components,
            facets=facets,
        )
        note_path = out / vault_path(facets, jira_key)  # <도메인>/<기능영역>/<KEY>.md
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(markdown, encoding="utf-8")
        index_entries.append((jira_key, knowledge.summary, facets))
        written += 1

    (out / "index.md").write_text(index_markdown(index_entries), encoding="utf-8")
    _logger.info("obsidian.exported", written=written, skipped=skipped, out_dir=str(out))
    return ExportResult(out_dir=str(out), written=written, skipped=skipped)
