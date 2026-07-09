"""되먹임(feedback) — 지식 구멍(gap) 집계.

`/ask` 가 근거를 못 찾거나 약할 때 남긴 질문(query_gaps)을 모아, "자주 묻는데 답 못하는 것"을
드러낸다. 이것이 "다음에 무엇을 위키화·수집할지"의 신호다(target-service 되먹임 루프).

순수 함수 — DB 접근 없음(조립 계층이 레코드를 읽어 넘긴다).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class GapRecord:
    """한 번의 '못 답함' 기록(query_gaps 한 행)."""

    question: str
    hit_count: int
    top_score: float


@dataclass(frozen=True)
class GapCluster:
    """같은(정규화) 질문의 묶음 — 되먹임 우선순위 단위."""

    question: str  # 대표 질문(가장 긴 원문)
    occurrences: int  # 몇 번 물었나(=빈도 신호)
    avg_top_score: float  # 평균 최상위 유사도(낮을수록 커버리지 부족)
    variants: int  # 표현 변형 수


def _normalize(question: str) -> str:
    """그룹핑용 정규화 — 소문자 + 공백 정규화(의미 있는 문장부호는 유지)."""
    return " ".join(question.lower().split())


def aggregate_gaps(records: Sequence[GapRecord], limit: int = 20) -> list[GapCluster]:
    """gap 레코드를 유사질문으로 묶어 우선순위 순으로 반환한다.

    정렬: 빈도(occurrences) 내림차순 → 평균 유사도(avg_top_score) 오름차순
    (자주 묻는데 커버리지가 낮은 것부터).
    """
    groups: dict[str, list[GapRecord]] = {}
    for record in records:
        groups.setdefault(_normalize(record.question), []).append(record)

    clusters = [
        GapCluster(
            question=max(items, key=lambda item: len(item.question)).question,
            occurrences=len(items),
            avg_top_score=sum(item.top_score for item in items) / len(items),
            variants=len({item.question for item in items}),
        )
        for items in groups.values()
    ]
    clusters.sort(key=lambda cluster: (-cluster.occurrences, cluster.avg_top_score))
    return clusters[:limit]
