"""Obsidian 마크다운 포매터 단위 테스트(순수)."""

from __future__ import annotations

from datetime import UTC, datetime

from modules.knowledge.domain.entity import Knowledge
from modules.knowledge.presentation.obsidian import (
    domain_moc_markdown,
    index_markdown,
    jira_key_of,
    moc_notes,
    standalone_vault_path,
    to_markdown,
    vault_filename,
    vault_path,
)

_FACETS = {
    "domain": "product",
    "feature_area": "option",
    "action": "수정",
    "channel": "쿠팡",
    "issue_type": "오류",
    "team": "툴",
    "area": "엔진",
}


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
    md = to_markdown(
        _wiki(), jira_key="PA20-19864", components=("상품-오류-엔진", "쿠팡"), facets=_FACETS
    )
    assert md.startswith("---\n")
    assert 'jira_key: "PA20-19864"' in md
    assert "trust: derived" in md
    assert "shelf/상품-오류-엔진" in md  # 컴포넌트 → 태그
    assert '"[쿠팡] 옵션 수정 오류"' in md  # 대괄호 제목은 YAML 인용
    assert "## 근본원인" in md and "플래그 미반영" in md
    assert "svc.py, opt.py" in md  # 리스트 code_refs 평탄화


def test_to_markdown_has_facet_tags_and_breadcrumb() -> None:
    md = to_markdown(_wiki(), jira_key="PA20-19864", facets=_FACETS)
    assert "domain/product" in md and "feature-area/option" in md
    assert "channel/쿠팡" in md
    assert "분류: 상품 > option > 수정" in md  # 도메인 한글 표시명


def test_standalone_knowledge_without_issue() -> None:
    # 이슈에 안 매인 verified 지식(sources 에 issue: 없음, issue_id 없음)
    wiki = _wiki(
        id="a235a252-80fa-5d6e-affc-8ac636b5013a",
        issue_id="",
        summary="[주문] 추가 컬럼(addcol) 기능",
        sources=("expert-authored",),
        source="verified",
    )
    # 전용 폴더 + slug + id8 파일명(도메인 트리에 섞이지 않음)
    path = standalone_vault_path(wiki)
    assert path.startswith("검증지식/")
    assert path.endswith("-a235a252.md")
    # 제목에 uuid 가 노출되지 않는다(요약만) + trust=verified
    md = to_markdown(wiki)
    assert md.startswith("---")
    assert "# [주문] 추가 컬럼(addcol) 기능" in md
    assert "a235a252" not in md.split("\n# ")[1].splitlines()[0]  # 제목 라인에 uuid 없음
    assert "trust: verified" in md


def test_vault_path_organizes_by_domain_feature() -> None:
    assert vault_path(_FACETS, "PA20-19864") == "상품/option/PA20-19864.md"
    assert vault_path({}, "PA20-1") == "미상/미상/PA20-1.md"  # facet 없으면 미상 폴더


def test_to_markdown_related_wikilinks_dedup_and_self_excluded() -> None:
    md = to_markdown(
        _wiki(),
        jira_key="PA20-19864",
        related_keys=["PA20-19780", "PA20-19864"],  # 자기 자신 포함 + body 와 중복
    )
    assert "- [[PA20-19780]]" in md
    assert md.count("[[PA20-19864]]") == 0  # 자기 자신은 링크 안 함
    assert md.count("[[PA20-19780]]") == 1  # related_keys + body 중복 → 1회


_INDEX_ENTRIES = [
    ("PA20-1", "옵션 오류", {"domain": "product", "feature_area": "option"}),
    ("PA20-2", "매칭", {"domain": "product", "feature_area": "matching"}),
    ("ENG-1", "주문", {"domain": "order", "feature_area": "미상"}),
]


def test_index_markdown_links_only_to_domain_mocs() -> None:
    """루트 index 는 이슈를 직접 링크하지 않고 도메인 MOC 노트로만 링크한다(별 모양 방지)."""
    md = index_markdown(_INDEX_ENTRIES)
    assert "총 3건 · 도메인 2개" in md
    assert "[[상품]]" in md and "(2건)" in md  # product → 상품 MOC, 2건
    assert "[[주문]]" in md
    assert "[[PA20-1]]" not in md  # 이슈는 index 에서 직접 링크하지 않음 → 계층 유지


def test_domain_moc_groups_issues_by_feature() -> None:
    md = domain_moc_markdown("상품", _INDEX_ENTRIES[:2])
    assert "# 상품" in md
    assert "[[index]]" in md  # 상위(index) 로 되짚는 링크
    assert "## option (1)" in md and "## matching (1)" in md
    assert "- [[PA20-1]] — 옵션 오류" in md


def test_moc_notes_emits_root_index_and_domain_notes() -> None:
    notes = dict(moc_notes(_INDEX_ENTRIES))
    assert set(notes) == {"index.md", "상품.md", "주문.md"}
    assert "[[상품]]" in notes["index.md"]
    assert "[[PA20-1]]" in notes["상품.md"]  # 이슈 링크는 도메인 MOC 안에
