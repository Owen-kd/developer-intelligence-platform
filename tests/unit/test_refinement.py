"""정제 계층(노이즈 필터 + 가치 게이트) 단위 테스트 — 결정적, 실측 노이즈 기반."""

from __future__ import annotations

from modules.knowledge.application.refinement import (
    assess,
    filter_comments,
    is_noise_comment,
    is_wiki_worthy,
)


def test_short_replies_are_noise() -> None:
    # 실측 단답 노이즈
    for reply in ("넵", "넹", "안돼", "배포완료", "감사합니다", "확인했습니다", "짱짱짱"):
        assert is_noise_comment(reply) is True


def test_blocklist_phrase_is_noise_regardless_of_punct() -> None:
    assert is_noise_comment("처리 완료되었습니다!") is True
    assert is_noise_comment("반영 완료했습니다.") is True


def test_substantive_comment_kept_even_with_완료() -> None:
    # '완료' 를 포함해도 실제 내용이 있으면 보존(부분매칭 아님)
    comment = "옵션 수정여부 로직 확인 완료했고, option_code 비교부에 버그가 있어 수정 필요합니다"
    assert is_noise_comment(comment) is False


def test_filter_removes_noise_and_dedup() -> None:
    comments = (
        "넵",  # 단답
        "처리 완료되었습니다",  # 블록리스트
        "option_code 와 vendorItemId 비교 로직에서 회귀가 발생했습니다",  # 실질
        "option_code 와 vendorItemId 비교 로직에서 회귀가 발생했습니다",  # 근접중복
    )
    kept = filter_comments(comments)
    assert len(kept) == 1
    assert "option_code" in kept[0]


def test_wiki_worthy_gate() -> None:
    # 신호 없음(빈 본문 + 코멘트 전부 노이즈 + 커밋 0) → 인덱스만
    assert is_wiki_worthy(description="", kept_comments=(), commit_shas=()) is False
    # 본문 있음 → 생성
    assert is_wiki_worthy(description="x" * 40, kept_comments=(), commit_shas=()) is True
    # 유의미 코멘트 있음 → 생성
    assert is_wiki_worthy(description="", kept_comments=("실질 내용",), commit_shas=()) is True
    # 커밋 있음 → 생성
    assert is_wiki_worthy(description="", kept_comments=(), commit_shas=("abc",)) is True


def test_assess_combines_filter_and_gate() -> None:
    result = assess(
        ("넵", "처리 완료되었습니다"), description="", commit_shas=()
    )
    assert result.kept_comments == ()
    assert result.dropped == 2
    assert result.worthy is False
