"""이슈 Facet 규칙 분류기 단위 테스트 (순수) — ADR-015."""

from __future__ import annotations

from modules.knowledge.application.classification import (
    COMMON,
    UNKNOWN,
    Facets,
    classify_rule,
    validate_llm_facets,
)


def test_team_from_key_prefix() -> None:
    assert classify_rule([], [], "PA20-19864").team == "툴"
    assert classify_rule([], [], "ENG-8404").team == "엔진"
    assert classify_rule([], [], "XX-1").team == UNKNOWN


def test_real_issue_pa20_19864() -> None:
    # 실 데이터: components ["상품-오류-엔진","쿠팡"]
    f = classify_rule(
        ["상품-오류-엔진", "쿠팡"],
        [],
        "PA20-19864",
        summary="[쿠팡] 상품옵션 '수정안함' 설정 시에도 판매가/재고가 수정되는 오류",
    )
    assert f.domain == "product"
    assert f.issue_type == "오류"
    assert f.area == "엔진"
    assert f.channel == "쿠팡"
    assert f.feature_area == "option"  # '옵션' 키워드
    assert f.action == "수정"
    assert f.team == "툴"


def test_compound_component_decomposes() -> None:
    f = classify_rule(["주문-기능개선-툴"], [], "PA20-1")
    assert f.domain == "order"
    assert f.issue_type == "기능개선"
    assert f.area == "툴"


def test_esm_takes_priority_over_single_market() -> None:
    f = classify_rule(["상품"], [], "PA20-2", summary="옥션 지마켓 ESM 마스터 옵션 매칭")
    assert f.channel == "ESM"


def test_matching_action_and_feature() -> None:
    f = classify_rule(["상품"], [], "PA20-3", summary="SKU 자동매칭 결과 오류")
    assert f.feature_area == "matching"
    assert f.action == "자동매칭"  # '자동매칭'이 '매칭'보다 우선


def test_unknown_when_no_signal() -> None:
    f = classify_rule(["[1:1문의]일반문의"], [], "PA20-4")
    assert f.domain == "inquiry-as"  # '문의' 토큰
    assert f.issue_type == "문의"
    assert f.feature_area == UNKNOWN  # 규칙으로 못 채움 → LLM 대상
    assert f.channel == COMMON


def test_validate_llm_fills_only_missing_axes() -> None:
    base = Facets(domain="product", feature_area=UNKNOWN, action=UNKNOWN, channel=COMMON)
    raw = {"domain": "order", "feature_area": "matching", "action": "자동매칭", "channel": "쿠팡"}
    out = validate_llm_facets(raw, base)
    assert out.domain == "product"  # 규칙이 채운 축은 LLM 이 못 덮음
    assert out.feature_area == "matching"  # 미상이던 축만 보강
    assert out.action == "자동매칭"
    assert out.channel == "쿠팡"


def test_validate_llm_rejects_out_of_vocab() -> None:
    base = Facets()
    raw = {"domain": "결제도메인", "feature_area": "새기능", "action": "짓기", "channel": "네이버"}
    out = validate_llm_facets(raw, base)
    assert out == base  # 통제 어휘 밖 값은 전부 무시(자유생성 방지)
