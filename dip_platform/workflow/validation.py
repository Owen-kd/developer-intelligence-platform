"""LLM 출력 검증 — 모델 출력을 신뢰하지 않고 항상 파싱/검증한다."""

from __future__ import annotations

import json

from shared.exceptions import ValidationError


def _strip_code_fence(text: str) -> str:
    """마크다운 코드펜스(```json ... ```)를 제거한다."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    inner = stripped[3:]
    if inner[:4].lower() == "json":
        inner = inner[4:]
    if inner.endswith("```"):
        inner = inner[:-3]
    return inner.strip()


def parse_json_output(raw: str, required: tuple[str, ...] = ()) -> dict[str, object]:
    """LLM 응답을 JSON 객체로 파싱하고 필수 키를 검증한다.

    실 LLM 은 코드펜스나 설명을 덧붙이기도 하므로, 펜스를 벗기고 본문의 첫 `{`~마지막 `}`
    구간을 재시도로 추출한다. 실패 시 ValidationError(폴백/재시도는 호출자 몫).
    """
    text = _strip_code_fence(raw)
    parsed: object
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValidationError("LLM 출력에서 JSON 객체를 찾지 못했다") from None
        try:
            parsed = json.loads(text[start : end + 1])
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValidationError(f"LLM 출력이 JSON 이 아니다: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValidationError("LLM 출력이 JSON 객체가 아니다")

    missing = [key for key in required if key not in parsed]
    if missing:
        raise ValidationError(f"LLM 출력에 필수 키 누락: {missing}")

    return parsed
