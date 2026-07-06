"""인증/권한 — 포트 + 정적 토큰 어댑터.

내부 도구 전제의 최소 모델([APR-009]): API 토큰 + 최소 역할(viewer/operator).
외부 IdP(OIDC) 는 같은 포트로 어댑터를 추가한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    """인증된 주체."""

    subject: str
    role: str


class Authenticator(ABC):
    """토큰 → Principal 검증 포트."""

    @abstractmethod
    def authenticate(self, token: str | None) -> Principal | None:
        """유효하면 Principal, 아니면 None."""


class StaticTokenAuthenticator(Authenticator):
    """토큰→Principal 매핑 기반 인증(로컬/내부 도구)."""

    def __init__(self, tokens: dict[str, Principal]) -> None:
        self._tokens = dict(tokens)

    def authenticate(self, token: str | None) -> Principal | None:
        if token is None:
            return None
        return self._tokens.get(token)
