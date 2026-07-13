"""위키 유형 게이트 단위 테스트 — 오류/기능개선만 위키화, 문의 스킵 (비용 제어)."""

from __future__ import annotations

from apps.wiki_pipeline import _wiki_type_allowed
from modules.knowledge.domain.entity import IssueSnapshot

_ALLOWED = frozenset({"오류", "기능개선"})


def _snap(summary: str, components: tuple[str, ...]) -> IssueSnapshot:
    return IssueSnapshot(
        issue_id="i",
        jira_key="PA20-1",
        summary=summary,
        status="열림",
        priority="P2",
        comments=(),
        commit_shas=(),
        source_event_ids=(),
        components=components,
    )


def test_error_issue_allowed() -> None:
    assert _wiki_type_allowed(_snap("쿠팡 옵션 수정 오류", ("상품-오류-툴",)), _ALLOWED)


def test_inquiry_skipped() -> None:
    # 문의 유형은 위키화 대상 아님 → 비용 절감
    assert not _wiki_type_allowed(_snap("배송 문의", ("[1:1문의]일반문의",)), _ALLOWED)


def test_empty_allowlist_permits_all() -> None:
    assert _wiki_type_allowed(_snap("문의", ("[1:1문의]일반문의",)), frozenset())
