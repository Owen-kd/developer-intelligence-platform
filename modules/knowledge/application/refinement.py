"""코멘트 정제(노이즈 필터) + 이슈 가치 게이트 — LLM 0, 결정적, 비파괴.

Context Before AI: AI 에 넣기 전에 맥락을 정제한다. 노이즈("넵", "처리 완료되었습니다" 등)는
위키 품질을 떨어뜨리고 토큰만 쓴다. 이 계층이 AI 컨텍스트용 'clean view' 를 만든다.

헌법("Never overwrite history"): **원본 코멘트는 지우지 않는다.** 이 계층은 순수 함수로
필터링된 뷰만 반환하며 DB 를 변경하지 않는다. 노이즈 목록은 코드가 아니라 설정 파일에서 로드
(`config/refinement/noise_phrases.txt`) — 운영이 조정 가능.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# 이 길이(trim 후 문자 수) 미만은 단답 노이즈로 간주한다("넵"·"안돼"·"배포완료" 등).
MIN_COMMENT_LEN = 12
# 위키 생성 가치 판단: 본문이 이 길이 이상이면 '실질 본문 있음'으로 본다.
MIN_DESCRIPTION_LEN = 30

_NOISE_FILE = (
    Path(__file__).resolve().parents[3] / "config" / "refinement" / "noise_phrases.txt"
)
_NORMALIZE_RE = re.compile(r"[\s\W_]+", re.UNICODE)


def _normalize(text: str) -> str:
    """비교용 정규화 — 공백/문장부호 제거 + 소문자. ('넵!' == '넵 ' == '넵')"""
    return _NORMALIZE_RE.sub("", text).lower()


@lru_cache(maxsize=1)
def _noise_phrases() -> frozenset[str]:
    if not _NOISE_FILE.is_file():
        return frozenset()
    phrases = set()
    for line in _NOISE_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        phrases.add(_normalize(stripped))
    return frozenset(phrases)


def is_noise_comment(body: str) -> bool:
    """단답이거나 노이즈 블록리스트에 완전 일치하면 노이즈로 판정한다(순수 함수)."""
    trimmed = body.strip()
    if len(trimmed) < MIN_COMMENT_LEN:
        return True
    return _normalize(trimmed) in _noise_phrases()


def filter_comments(comments: Sequence[str]) -> tuple[str, ...]:
    """노이즈·근접중복(정규화 동일)을 제거한 코멘트만 순서대로 반환한다(원본 미변경)."""
    kept: list[str] = []
    seen: set[str] = set()
    for comment in comments:
        if is_noise_comment(comment):
            continue
        key = _normalize(comment)
        if key in seen:  # 같은 말 반복(근접중복) 제거
            continue
        seen.add(key)
        kept.append(comment)
    return tuple(kept)


def is_wiki_worthy(
    *, description: str, kept_comments: Sequence[str], commit_shas: Sequence[str]
) -> bool:
    """정제 후 위키 생성 가치가 있는가.

    실질 본문 · 유의미 코멘트 · 링크된 커밋 중 하나라도 있으면 생성한다.
    셋 다 없으면(예: "안됨"·"처리완료"만 있는 이슈) 제목+상태만 인덱싱(LLM 비용 0).
    """
    if len(description.strip()) >= MIN_DESCRIPTION_LEN:
        return True
    if kept_comments:
        return True
    return bool(commit_shas)


@dataclass(frozen=True)
class Refinement:
    """이슈 정제 결과 — clean 코멘트 + 드롭 수 + 위키 생성 가치."""

    kept_comments: tuple[str, ...]
    dropped: int
    worthy: bool


def assess(
    comments: Sequence[str], *, description: str, commit_shas: Sequence[str]
) -> Refinement:
    """코멘트 정제 + 가치 게이트를 한 번에 평가한다(위키 생성 경로에서 호출)."""
    kept = filter_comments(comments)
    worthy = is_wiki_worthy(
        description=description, kept_comments=kept, commit_shas=commit_shas
    )
    return Refinement(kept_comments=kept, dropped=len(comments) - len(kept), worthy=worthy)
