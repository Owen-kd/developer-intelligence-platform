"""PII·시크릿 스크러빙 — 원천 텍스트에서 민감/노이즈 정보를 제거한다.

수집 시점에 적용해 **크리덴셜/개인정보가 DB에 저장되지 않도록** 한다.
- OpenAPI 호출/디버그/S3 URL 제거 (지식이 아니라 노이즈)
- 로그인 토큰(`info=eyJ...` = base64 이메일+비번) 제거 (크리덴셜)
- 이메일 → `[이메일]` 마스킹 (PII)
- 문의 푸터 라벨(문의링크/디버그 접속 등) 제거
결정론적(정규식) — LLM 불필요.
"""

from __future__ import annotations

import re

_URL = re.compile(r"https?://\S+")
_TOKEN = re.compile(r"info=eyJ\S+")  # base64 로그인 토큰(이메일+비밀번호)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_LABELS = re.compile(
    r"(문의링크|디버그\s*접속|업체이메일|업체\s*솔루션\s*번호|"
    r"테스트\s*동의여부|판매자센터\s*접속\s*동의\s*여부)\s*[:：]?\s*"
)
_HWS = re.compile(r"[^\S\n]+")  # 가로 공백(스페이스/탭)만 — 개행은 보존
_NL_TRIM = re.compile(r"[ \t]*\n[ \t]*")  # 개행 주변 가로 공백 제거
_NL_COLLAPSE = re.compile(r"\n{3,}")  # 빈 줄 3개 이상 → 2개(문단 구분은 유지)


def scrub_text(text: str) -> str:
    """민감/노이즈 정보를 제거한 안전 텍스트를 반환한다(빈 입력은 그대로).

    개행은 보존한다 — 본문의 단계/목록/코드 구조가 임베딩·위키 품질에 필요하기 때문.
    """
    if not text:
        return text
    text = _URL.sub("", text)  # 디버그/API/S3 URL (토큰도 URL에 붙어 있으면 함께 제거)
    text = _TOKEN.sub("", text)  # 남은 로그인 토큰
    text = _EMAIL.sub("[이메일]", text)  # PII 마스킹
    text = _LABELS.sub("", text)  # 문의 푸터 라벨
    text = _HWS.sub(" ", text)  # 가로 공백만 축소(개행 유지 → 구조 보존)
    text = _NL_TRIM.sub("\n", text)  # 개행 주변 공백 제거
    text = _NL_COLLAPSE.sub("\n\n", text)  # 과도한 빈 줄만 축소(단계/목록/문단 유지)
    return text.strip()
