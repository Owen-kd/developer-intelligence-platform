"""FastAPI 의존성 — 조립된 DIP 애플리케이션 컨테이너 접근."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from apps.composition import DipInMemoryApp


def get_container(request: Request) -> DipInMemoryApp:
    """lifespan 에서 초기화된 인메모리 애플리케이션을 반환한다."""
    container = getattr(request.app.state, "dip", None)
    if container is None:
        raise RuntimeError("DIP container 가 초기화되지 않았다(lifespan 미실행)")
    return cast(DipInMemoryApp, container)
