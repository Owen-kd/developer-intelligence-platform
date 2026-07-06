"""마이그레이션 discovery 단위 테스트 — 파일명 순서 보장(순수 로직)."""

from __future__ import annotations

from pathlib import Path

from apps.cli.migrate import discover_migrations


def test_discover_orders_by_filename(tmp_path: Path) -> None:
    (tmp_path / "002_b.sql").write_text("-- b", encoding="utf-8")
    (tmp_path / "001_a.sql").write_text("-- a", encoding="utf-8")
    (tmp_path / "010_c.sql").write_text("-- c", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    result = [path.name for path in discover_migrations(tmp_path)]

    assert result == ["001_a.sql", "002_b.sql", "010_c.sql"]
