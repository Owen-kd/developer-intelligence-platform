"""공통 상수. 매직 넘버/문자열은 여기로 모은다."""

from __future__ import annotations

# Context 조립 기본 토큰 예산.
DEFAULT_TOKEN_BUDGET = 2000

# 토큰 추정용 대략적 문자/토큰 비율(결정적 추정).
CHARS_PER_TOKEN = 4

__all__ = ["CHARS_PER_TOKEN", "DEFAULT_TOKEN_BUDGET"]
