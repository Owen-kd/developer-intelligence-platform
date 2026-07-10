"""Obsidian 마크다운 포매터 단위 테스트(순수)."""

from __future__ import annotations

from datetime import UTC, datetime

from modules.knowledge.domain.entity import Knowledge
from modules.knowledge.presentation.obsidian import (
    index_markdown,
    jira_key_of,
    to_markdown,
    vault_filename,
)


def _wiki(**over: object) -> Knowledge:
    base: dict[str, object] = dict(
        id="k1",
        type="wiki",
        issue_id="i1",
        summary="[쿠팡] 옵션 수정 오류",
        body={
            "symptom": "수정이 안 됨",
            "root_cause": "플래그 미반영",
            "resolution": "패치",
            "code_refs": ["svc.py", "opt.py"],
            "content": "본문",
            "related_issues": ["PA20-19780", "PA20-19864"],
        },
        sources=("issue:PA20-19864", "comment:1"),
        created_at=datetime(2026, 7, 10, tzinfo=UTC),
        source="derived",
    )
    base.update(over)
    return Knowledge(**base)  # type: ignore[arg-type]


def test_jira_key_of_reads_source_prefix() -> None:
    assert jira_key_of(_wiki()) == "PA20-19864"
    assert jira_key_of(_wiki(sources=("comment:1",))) is None


def test_vault_filename_sanitizes() -> None:
    assert vault_filename("PA20-19864") == "PA20-19864.md"
    assert vault_filename("a/b:c") == "a-b-c.md"
    assert vault_filename("!!!") == "wiki.md"  # 빈 결과 폴백


def test_to_markdown_has_frontmatter_and_sections() -> None:
    md = to_markdown(_wiki(), jira_key="PA20-19864", components=("상품-오류-엔진", "쿠팡"))
    assert md.startswith("---\n")
    assert 'jira_key: "PA20-19864"' in md
    assert "trust: derived" in md
    assert "shelf/상품-오류-엔진" in md  # 컴포넌트 → 태그
    assert '"[쿠팡] 옵션 수정 오류"' in md  # 대괄호 제목은 YAML 인용
    assert "## 근본원인" in md and "플래그 미반영" in md
    assert "svc.py, opt.py" in md  # 리스트 code_refs 평탄화


def test_to_markdown_related_wikilinks_dedup_and_self_excluded() -> None:
    md = to_markdown(
        _wiki(),
        jira_key="PA20-19864",
        related_keys=["PA20-19780", "PA20-19864"],  # 자기 자신 포함 + body 와 중복
    )
    assert "- [[PA20-19780]]" in md
    assert md.count("[[PA20-19864]]") == 0  # 자기 자신은 링크 안 함
    assert md.count("[[PA20-19780]]") == 1  # related_keys + body 중복 → 1회


def test_index_markdown_groups_by_shelf() -> None:
    md = index_markdown(
        [
            ("PA20-1", "옵션 오류", ("쿠팡",)),
            ("PA20-2", "바코드", ("쿠팡",)),
            ("ENG-1", "엔진", ()),
        ]
    )
    assert "총 3건" in md
    assert "## 쿠팡 (2)" in md
    assert "## (미분류) (1)" in md
    assert "- [[PA20-1]] — 옵션 오류" in md
