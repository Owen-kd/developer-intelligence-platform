"""dip_platform.access — 접근제어(팀별 서가 열람) 정책. ADR-010."""

from .policy import allowed_patterns, load_policies

__all__ = ["allowed_patterns", "load_policies"]
