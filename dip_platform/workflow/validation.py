"""LLM 출력 검증 — 모델 출력을 신뢰하지 않고 항상 파싱/검증한다."""

from __future__ import annotations

import json

from shared.exceptions import ValidationError


def parse_json_output(raw: str, required: tuple[str, ...] = ()) -> dict[str, object]:
    """LLM 응답 문자열을 JSON 객체로 파싱하고 필수 키를 검증한다.

    실패 시 ValidationError 를 던진다(폴백/재시도는 호출자 몫).
    """
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValidationError(f"LLM 출력이 JSON 이 아니다: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValidationError("LLM 출력이 JSON 객체가 아니다")

    missing = [key for key in required if key not in parsed]
    if missing:
        raise ValidationError(f"LLM 출력에 필수 키 누락: {missing}")

    return parsed
