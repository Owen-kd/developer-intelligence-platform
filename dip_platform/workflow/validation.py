"""LLM 출력 검증 — 모델 출력을 신뢰하지 않고 항상 파싱/검증한다.

실 LLM 은 흔히 JSON 을 ```json 코드펜스로 감싸거나 앞뒤에 설명을 붙인다.
따라서 파싱 전에 코드펜스를 벗기고, 실패하면 첫 `{`~마지막 `}` 구간을 추출해 재시도한다.
추출 후에도 스키마(필수 키/타입)는 그대로 엄격히 검증한다.
"""

from __future__ import annotations

import json

from shared.exceptions import ValidationError


def _strip_code_fence(text: str) -> str:
    """```json ... ``` / ``` ... ``` 코드펜스를 벗긴다(없으면 원문)."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    # 첫 줄(``` 또는 ```json 등)을 제거
    body = stripped.split("\n", 1)[1] if "\n" in stripped else ""
    fence_end = body.rfind("```")
    if fence_end != -1:
        body = body[:fence_end]
    return body.strip()


def _loads_lenient(raw: str) -> object:
    """코드펜스 제거 후 json.loads. 실패하면 첫 `{`~마지막 `}` 구간으로 재시도."""
    candidate = _strip_code_fence(raw)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise
        return json.loads(candidate[start : end + 1])


def parse_json_output(raw: str, required: tuple[str, ...] = ()) -> dict[str, object]:
    """LLM 응답 문자열을 JSON 객체로 파싱하고 필수 키를 검증한다.

    실패 시 ValidationError 를 던진다(폴백/재시도는 호출자 몫).
    """
    try:
        parsed = _loads_lenient(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValidationError(f"LLM 출력이 JSON 이 아니다: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValidationError("LLM 출력이 JSON 객체가 아니다")

    missing = [key for key in required if key not in parsed]
    if missing:
        raise ValidationError(f"LLM 출력에 필수 키 누락: {missing}")

    return parsed
