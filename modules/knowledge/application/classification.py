"""이슈 Facet 규칙 분류기 (순수, LLM 0) — [ADR-015] 1단계 부트스트랩.

Jira component/label/키prefix 를 통제 어휘 facet 으로 분해한다. 규칙으로 못 채우는 축
(기능영역·액션·문의성 도메인)은 `미상` 으로 두고 후속 LLM 보강 대상으로 남긴다.
통제 어휘는 백엔드 도메인 문서(domain-map/glossary/domains/product)에 정렬한다.
상세: `.ai/knowledge/taxonomy.md`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

UNKNOWN = "미상"
COMMON = "공통"

# 도메인: Jira 한글 토큰 → domain-map 레지스트리 키(안정적 식별자)
_DOMAIN_BY_TOKEN: tuple[tuple[str, str], ...] = (
    ("상품", "product"),
    ("주문", "order"),
    ("재고", "stock"),
    ("결제", "pay"),
    ("정산", "calculate"),
    ("통계", "stats"),
    ("배송", "delivery"),
    ("회원", "user"),
    ("설정", "settings"),
    ("작업", "work"),
    ("문의", "inquiry-as"),
)
# 유형: component 토큰(구체적인 것 먼저)
_TYPE_RULES: tuple[tuple[str, str], ...] = (
    ("기능개선", "기능개선"),
    ("버그", "오류"),
    ("오류", "오류"),
    ("문의", "문의"),
    ("정책", "정책"),
    ("개선", "기능개선"),
)
# 영역: 어느 시스템이 영향받나(component 접미사/토큰)
_AREA_RULES: tuple[tuple[str, str], ...] = (
    ("엔진", "엔진"),
    ("백오피스", "백오피스"),
    ("툴", "툴"),
)
# 채널: glossary §2 마켓명(ESM=옥션+지마켓 통합은 별도 우선 처리)
_CHANNELS: tuple[str, ...] = (
    "쿠팡",
    "스마트스토어",
    "11번가",
    "인터파크",
    "위메프",
    "홈플러스",
    "카카오톡스토어",
    "아임웹",
    "Qoo10",
    "GSSHOP",
    "더현대",
    "이지웰몰",
    "SSG",
)
# 기능영역(product 확정): 키워드 → feature-area. 구체적인 것 먼저.
_FEATURE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("옵션관리코드", "옵션"), "option"),
    (("자동세팅", "수집"), "scrap"),
    (("매칭",), "matching"),
    (("카테고리",), "category"),
    (("추가구매", "추가항목"), "add-option"),
    (("템플릿",), "template"),
    (("머리말", "꼬리말", "머리글", "꼬리글"), "addcontent"),
    (("고시",), "noti"),
    (("키워드", "상품명"), "keyword-ai"),
    (("엑셀", "일괄"), "excel"),
    (("등록", "수정", "삭제", "상세"), "online"),
)
# 액션: 키워드 → action. 구체적인 것(매칭해제/자동매칭) 먼저.
_ACTION_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("매칭해제", "매칭 해제"), "매칭해제"),
    (("자동매칭",), "자동매칭"),
    (("자동세팅",), "자동세팅"),
    (("수집",), "수집"),
    (("매칭",), "매칭"),
    (("등록", "추가", "생성"), "등록"),
    (("일괄수정", "일괄 수정"), "일괄수정"),
    (("수정", "변경", "편집"), "수정"),
    (("삭제", "제거"), "삭제"),
    (("복사",), "복사"),
    (("조회", "상세", "노출"), "조회"),
    (("동기화", "연동"), "동기화"),
)


@dataclass(frozen=True)
class Facets:
    """이슈의 6축 분류 결과(값 없으면 `미상`/`공통`)."""

    domain: str = UNKNOWN
    feature_area: str = UNKNOWN
    action: str = UNKNOWN
    channel: str = COMMON
    issue_type: str = UNKNOWN
    team: str = UNKNOWN
    area: str = UNKNOWN


def _team_from_key(jira_key: str) -> str:
    prefix = jira_key.split("-", 1)[0].upper()
    if prefix == "PA20":
        return "툴"
    if prefix == "ENG":
        return "엔진"
    return UNKNOWN


def _first_match(haystack: str, rules: Sequence[tuple[str, str]]) -> str | None:
    for token, value in rules:
        if token in haystack:
            return value
    return None


def _first_keyword_match(
    haystack: str, rules: Sequence[tuple[tuple[str, ...], str]]
) -> str | None:
    for keywords, value in rules:
        if any(kw in haystack for kw in keywords):
            return value
    return None


def classify_rule(
    components: Sequence[str],
    labels: Sequence[str],
    jira_key: str,
    summary: str = "",
) -> Facets:
    """규칙만으로 facet 을 채운다(LLM 0). 못 채운 축은 `미상`/`공통`."""
    comp_text = " ".join(components)
    # 채널/기능영역/액션은 요약문 신호도 활용(정확 토큰은 comp, 자연어는 summary)
    signal = f"{comp_text} {' '.join(labels)} {summary}"

    domain = _first_match(comp_text, _DOMAIN_BY_TOKEN) or UNKNOWN
    issue_type = _first_match(comp_text, _TYPE_RULES) or UNKNOWN
    area = _first_match(comp_text, _AREA_RULES) or UNKNOWN

    # 채널: ESM(옥션+지마켓)은 개별 마켓보다 우선(통합 개념)
    channel = COMMON
    if ("옥션" in signal and "지마켓" in signal) or "ESM" in signal:
        channel = "ESM"
    elif "옥션" in signal:
        channel = "옥션"
    elif "지마켓" in signal:
        channel = "지마켓"
    else:
        for market in _CHANNELS:
            if market in signal:
                channel = market
                break

    feature_area = _first_keyword_match(signal, _FEATURE_RULES) or UNKNOWN
    action = _first_keyword_match(signal, _ACTION_RULES) or UNKNOWN

    return Facets(
        domain=domain,
        feature_area=feature_area,
        action=action,
        channel=channel,
        issue_type=issue_type,
        team=_team_from_key(jira_key),
        area=area,
    )
