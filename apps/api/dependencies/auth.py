"""API 인증 의존성 — Bearer 토큰 검증 + 접근 감사.

인증/권한은 platform/auth 로 일원화하고, 접근은 감사(audit)에 남긴다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dip_platform.auth import Authenticator, Principal, StaticTokenAuthenticator
from shared.config.settings import get_settings

_bearer = HTTPBearer(auto_error=False)


def _authenticator() -> Authenticator:
    settings = get_settings()
    return StaticTokenAuthenticator(
        {settings.api_token: Principal(subject="local-dev", role="operator")}
    )


async def require_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    token = credentials.credentials if credentials is not None else None
    principal = _authenticator().authenticate(token)

    container = getattr(request.app.state, "dip", None)
    if container is not None:
        await container.audit.record(
            "api.access" if principal is not None else "api.auth_failed",
            {
                "path": request.url.path,
                "subject": principal.subject if principal is not None else None,
            },
        )

    if principal is None:
        raise HTTPException(status_code=401, detail="유효한 인증 토큰이 필요하다")
    return principal
