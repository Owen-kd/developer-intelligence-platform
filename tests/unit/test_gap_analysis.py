"""gap 집계(aggregate_gaps) 단위 테스트 — 되먹임 우선순위."""

from __future__ import annotations

from modules.knowledge.application.gap_analysis import GapRecord, aggregate_gaps


def test_groups_and_counts_occurrences() -> None:
    records = [
        GapRecord("쿠팡 옵션 안됨", 3, 0.70),
        GapRecord("쿠팡 옵션 안됨", 3, 0.60),
        GapRecord("배송 문의", 1, 0.50),
    ]
    clusters = aggregate_gaps(records)
    assert clusters[0].question == "쿠팡 옵션 안됨"
    assert clusters[0].occurrences == 2
    assert abs(clusters[0].avg_top_score - 0.65) < 1e-6


def test_ties_ranked_by_low_coverage_first() -> None:
    records = [GapRecord("A질문", 1, 0.90), GapRecord("B질문", 1, 0.30)]
    clusters = aggregate_gaps(records)
    assert clusters[0].question == "B질문"  # 동일 빈도 → 낮은 유사도 우선


def test_normalize_groups_case_and_whitespace() -> None:
    records = [GapRecord("쿠팡  옵션", 1, 0.5), GapRecord("쿠팡 옵션", 1, 0.5)]
    clusters = aggregate_gaps(records)
    assert len(clusters) == 1
    assert clusters[0].variants == 2
