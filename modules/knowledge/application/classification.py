"""이슈 Facet 규칙 분류기 (순수, LLM 0) — [ADR-015] 1단계 부트스트랩.

Jira component/label/키prefix 를 통제 어휘 facet 으로 분해한다. 규칙으로 못 채우는 축
(기능영역·액션·문의성 도메인)은 `미상` 으로 두고 후속 LLM 보강 대상으로 남긴다.
통제 어휘는 백엔드 도메인 문서(domain-map/glossary/domains/product)에 정렬한다.
상세: `.ai/knowledge/taxonomy.md`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

UNKNOWN = "미상"
COMMON = "공통"

# 도메인 키(domain-map 레지스트리) → 한글 표시명(폴더·인덱스용)
DOMAIN_LABELS: dict[str, str] = {
    "product": "상품",
    "order": "주문",
    "stock": "재고",
    "pay": "결제",
    "calculate": "정산",
    "inquiry-as": "문의",
    "stats": "통계",
    "delivery": "배송",
    "user": "회원",
    "settings": "설정",
    "work": "작업",
    UNKNOWN: UNKNOWN,
}


def domain_label(domain: str) -> str:
    """도메인 키를 한글 표시명으로(없으면 키 그대로)."""
    return DOMAIN_LABELS.get(domain, domain)

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


# 통제 어휘(LLM 보강 검증용) — LLM 출력이 이 목록에 없으면 미상으로 폴백(자유생성 금지).
DOMAIN_VOCAB: frozenset[str] = frozenset(
    {
        "product", "order", "stock", "pay", "calculate", "inquiry-as",
        "stats", "delivery", "user", "settings", "work",
    }
)
# 기능영역(중분류)은 도메인별로 다르다 — 백엔드 도메인 문서(gmp.openapi.2023/.ai/domains)에서 추출.
# 도메인-스코프 검증으로 order 기능이 product 이슈에 붙는 것을 막는다.
FEATURE_BY_DOMAIN: dict[str, frozenset[str]] = {
    "product": frozenset(
        {
            "online", "matching", "category", "template", "setinfo", "add-option",
            "addcontent", "noti", "keyword-ai", "excel", "scrap", "option",
        }
    ),
    "order": frozenset(
        {"order", "matching", "invoice", "as", "gift", "package", "tag", "manage", "excel"}
    ),
    "stock": frozenset(
        {"base", "inventory", "depot", "set", "supplier", "style", "barcode", "excel"}
    ),
    "work": frozenset({"work", "result", "automatch", "scheduler", "excel"}),
}
FEATURE_VOCAB: frozenset[str] = frozenset().union(*FEATURE_BY_DOMAIN.values())
ACTION_VOCAB: frozenset[str] = frozenset(
    {
        "등록", "수정", "삭제", "조회", "복사", "일괄수정", "매칭", "매칭해제",
        "자동매칭", "수집", "자동세팅", "상태변경", "동기화", "연동", "정책",
    }
)
CHANNEL_VOCAB: frozenset[str] = frozenset(
    {
        "쿠팡", "옥션", "지마켓", "ESM", "스마트스토어", "11번가", "SSG", "인터파크",
        "위메프", "홈플러스", "카카오톡스토어", "아임웹", "Qoo10", "GSSHOP",
        "더현대", "이지웰몰",
    }
)

# 고정 어휘 축(도메인/액션/채널). 기능영역은 도메인-스코프라 아래서 별도 처리.
_LLM_AXES: tuple[tuple[str, frozenset[str], str], ...] = (
    ("domain", DOMAIN_VOCAB, UNKNOWN),
    ("action", ACTION_VOCAB, UNKNOWN),
    ("channel", CHANNEL_VOCAB, COMMON),
)


def validate_llm_facets(raw: Mapping[str, object], current: Facets) -> Facets:
    """LLM 분류 결과를 통제 어휘로 검증해, **규칙이 못 채운 축만** 보강한다(비파괴).

    - 규칙이 이미 채운 축(미상/공통 아님)은 LLM 값으로 덮지 않는다(규칙 우선).
    - LLM 값이 통제 어휘에 없으면 무시(자유생성 방지). 팀/영역/유형은 규칙 전용(보강 대상 아님).
    - 기능영역은 **도메인-스코프**: 그 도메인의 기능영역만 허용(order 기능이 product 에 안 붙게).
    """
    updates: dict[str, str] = {}
    for axis, vocab, empty in _LLM_AXES:
        if getattr(current, axis) != empty:
            continue  # 규칙이 이미 채움 → 유지
        value = raw.get(axis)
        if isinstance(value, str) and value in vocab:
            updates[axis] = value
    # 기능영역: 도메인(방금 보강됐을 수도)에 맞는 어휘만 허용
    if current.feature_area == UNKNOWN:
        domain = updates.get("domain", current.domain)
        allowed = FEATURE_BY_DOMAIN.get(domain, frozenset())
        value = raw.get("feature_area")
        if isinstance(value, str) and value in allowed:
            updates["feature_area"] = value
    return replace(current, **updates) if updates else current


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

    # 기능영역 규칙(_FEATURE_RULES)은 product 전용 키워드다 — product 도메인에만 적용해
    # order/stock 이슈에 product 기능영역(option/scrap 등)이 오염되지 않게 한다(도메인-인지).
    # 비-product 는 미상으로 두고 LLM 이 도메인-스코프 어휘로 채운다.
    feature_area = UNKNOWN
    if domain == "product":
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
