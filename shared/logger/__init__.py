"""구조화 로깅. `print` 금지 — 모든 로그는 이 모듈을 경유한다.

키=값 형태로 구조화하고, correlation id 를 남길 수 있게 한다.
초기 구현은 stdlib logging 위의 얇은 래퍼다(브로커/수집기 교체 여지 유지).
"""

from __future__ import annotations

import logging
import sys
from typing import Any

_CONFIGURED = False


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger("dip")
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.propagate = False
    _CONFIGURED = True


def _render(fields: dict[str, Any]) -> str:
    return " ".join(f"{key}={value!r}" for key, value in fields.items())


class StructuredLogger:
    """키=값 필드를 붙여 구조화 로그를 남기는 얇은 어댑터."""

    def __init__(self, name: str) -> None:
        _configure_root()
        self._log = logging.getLogger(f"dip.{name}")

    def info(self, message: str, **fields: Any) -> None:
        self._log.info("%s %s", message, _render(fields))

    def warning(self, message: str, **fields: Any) -> None:
        self._log.warning("%s %s", message, _render(fields))

    def error(self, message: str, **fields: Any) -> None:
        self._log.error("%s %s", message, _render(fields))


def get_logger(name: str) -> StructuredLogger:
    """이름 있는 구조화 로거를 반환한다."""
    return StructuredLogger(name)
