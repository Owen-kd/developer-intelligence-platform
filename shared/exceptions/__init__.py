"""도메인 예외 계층. 조용히 삼키지 않고, 내부/사용자 메시지를 구분한다."""

from __future__ import annotations


class DipError(Exception):
    """DIP 도메인 예외의 베이스."""


class ValidationError(DipError):
    """입력/산출물이 스키마·불변식을 만족하지 못했다."""


class NotFoundError(DipError):
    """요청한 리소스를 찾을 수 없다."""


__all__ = ["DipError", "NotFoundError", "ValidationError"]
