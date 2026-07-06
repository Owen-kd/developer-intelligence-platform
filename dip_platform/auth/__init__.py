"""dip_platform.auth — 인증/권한."""

from .authenticator import Authenticator, Principal, StaticTokenAuthenticator

__all__ = ["Authenticator", "Principal", "StaticTokenAuthenticator"]
