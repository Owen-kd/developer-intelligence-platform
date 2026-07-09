"""접근제어 정책(팀별 서가) 단위 테스트 — 기본 deny."""

from __future__ import annotations

from pathlib import Path

from dip_platform.access import allowed_patterns, load_policies


def test_load_and_allowed_patterns(tmp_path: Path) -> None:
    policy_file = tmp_path / "team_shelves.txt"
    policy_file.write_text(
        "# 주석\ncommerce: 쿠팡, 상품%\ninfra: 배포%\n\n", encoding="utf-8"
    )
    policies = load_policies(str(policy_file))
    assert policies["commerce"] == ("쿠팡", "상품%")
    assert allowed_patterns(policies, "commerce") == ("쿠팡", "상품%")
    assert allowed_patterns(policies, "infra") == ("배포%",)


def test_unknown_team_is_default_deny(tmp_path: Path) -> None:
    policy_file = tmp_path / "team_shelves.txt"
    policy_file.write_text("commerce: 쿠팡\n", encoding="utf-8")
    policies = load_policies(str(policy_file))
    assert allowed_patterns(policies, "unknown-team") == ()
    assert allowed_patterns(policies, "") == ()


def test_missing_file_yields_empty_policies(tmp_path: Path) -> None:
    assert load_policies(str(tmp_path / "does_not_exist.txt")) == {}
