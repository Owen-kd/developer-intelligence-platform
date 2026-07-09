"""parse_json_output 의 실-LLM 관용 파싱 테스트.

실 모델은 JSON 을 코드펜스로 감싸거나 앞뒤에 설명을 붙인다. 그런 출력도
스키마 검증을 통과해야 한다(추출 후에도 필수 키/타입은 엄격 검증).
"""

from __future__ import annotations

import pytest

from dip_platform.workflow import parse_json_output
from shared.exceptions import ValidationError

_REQUIRED = ("category", "priority", "confidence", "rationale")
_OBJ = '{"category":"bug","priority":"high","confidence":0.6,"rationale":"결제 타임아웃"}'


def test_parses_json_fenced_output() -> None:
    raw = f"```json\n{_OBJ}\n```"
    parsed = parse_json_output(raw, required=_REQUIRED)
    assert parsed["category"] == "bug"
    assert parsed["priority"] == "high"


def test_parses_bare_fence_output() -> None:
    parsed = parse_json_output(f"```\n{_OBJ}\n```", required=_REQUIRED)
    assert parsed["confidence"] == 0.6


def test_parses_json_with_surrounding_prose() -> None:
    raw = f"분류 결과는 다음과 같습니다:\n{_OBJ}\n이상입니다."
    parsed = parse_json_output(raw, required=_REQUIRED)
    assert parsed["rationale"] == "결제 타임아웃"


def test_still_rejects_when_no_json_object() -> None:
    with pytest.raises(ValidationError):
        parse_json_output("```\n그냥 설명만 있고 객체가 없음\n```", required=_REQUIRED)
