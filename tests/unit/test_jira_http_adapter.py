"""실 Jira 어댑터의 순수 헬퍼 테스트 (네트워크 불필요)."""

from __future__ import annotations

from infrastructure.jira.client import _adf_to_text, _name


def test_adf_to_text_flattens_paragraphs() -> None:
    adf = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "첫 줄"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "둘째 줄"}]},
        ],
    }
    assert _adf_to_text(adf) == "첫 줄\n둘째 줄"


def test_adf_to_text_handles_empty_and_none() -> None:
    assert _adf_to_text(None) == ""
    assert _adf_to_text({}) == ""


def test_name_extracts_from_dict_or_blank() -> None:
    assert _name({"name": "Bug"}) == "Bug"
    assert _name(None) == ""
    assert _name({}) == ""
