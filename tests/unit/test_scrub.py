"""PII/시크릿 스크러버 테스트 — 크리덴셜은 제거, 실제 내용은 보존."""

from __future__ import annotations

from shared.utils.scrub import scrub_text


def test_removes_urls_tokens_emails_keeps_content() -> None:
    raw = (
        "택배사정보 저장 시 무한 로딩 발생하여 확인 요청 "
        "문의링크: https://admin.playauto.io/#!/question/detail/7632510"
        "업체이메일: ludensemall@gmail.com "
        "디버그 접속: https://app.playauto.io/adminLogin.html?info=eyJlbWFpbCI6IngifQ=="
    )
    out = scrub_text(raw)

    assert "무한 로딩" in out  # 실제 내용 보존
    assert "http" not in out  # URL 제거
    assert "info=eyJ" not in out  # 로그인 토큰 제거
    assert "@" not in out or "[이메일]" in out  # 이메일 마스킹
    assert "ludensemall" not in out


def test_empty_passthrough() -> None:
    assert scrub_text("") == ""
