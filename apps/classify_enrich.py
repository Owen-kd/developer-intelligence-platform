"""Facet 분류 LLM 보강 — 규칙이 못 채운 축(미상)을 고정어휘 LLM 으로 채운다. [ADR-015] 2단계.

규칙 부트스트랩(classify_bootstrap) 뒤에 돌린다. 도메인/기능영역/액션/채널이 `미상`/`공통` 인
이슈만 대상으로, 저가 모델(Haiku)에 요약+컴포넌트를 주고 통제 어휘 중 하나로 분류하게 한다.
LLM 출력은 통제 어휘로 검증(validate_llm_facets) — 목록 밖 값은 무시(자유생성 금지, 미상 유지).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from dip_platform.registry import FilePromptRegistry
from infrastructure.llm.client import LLMClient
from modules.jira.infrastructure.repository import PostgresIssueRepository
from modules.knowledge.application.classification import (
    Facets,
    classify_rule,
    validate_llm_facets,
)
from modules.knowledge.application.refinement import redact_pii
from shared.config.settings import Settings, get_settings
from shared.logger import get_logger

_logger = get_logger("classify.enrich")

_PROMPT = "knowledge/classify"


@dataclass
class EnrichResult:
    targets: int  # 보강 대상(미상 축이 있던 이슈) 수
    enriched: int  # 실제로 1축 이상 채워진 이슈 수
    failed: int  # LLM/파싱 실패로 건너뛴 수(정직 보고)


def _build_classify_llm(settings: Settings) -> tuple[LLMClient, str]:
    if settings.anthropic_api_key:
        from infrastructure.anthropic.client import AnthropicClient

        client = AnthropicClient(
            api_key=settings.anthropic_api_key,
            model=settings.classify_model,  # 저가 모델(Haiku) — 단순 분류
            max_tokens=256,  # JSON 한 줄이면 충분
        )
        return client, settings.classify_model
    from infrastructure.llm.client import FakeLLMClient

    return FakeLLMClient(response="{}"), "fake"


def _needs_enrichment(facets: Facets) -> bool:
    # 실제 gap 은 도메인/기능영역/액션 미상뿐. channel=공통 은 대부분 정상(마켓 무관)이라
    # 트리거에서 제외 — 이걸 넣으면 거의 전 이슈가 LLM 대상이 되어 비용 낭비. 채널은
    # 이 축들 때문에 호출될 때 함께 보강되는 보너스로 남긴다.
    return "미상" in (facets.domain, facets.feature_area, facets.action)


def _parse_json(text: str) -> dict[str, object]:
    """LLM 응답에서 JSON 객체를 관용적으로 뽑는다(코드펜스/잡텍스트 방어)."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def enrich_missing(limit: int | None = None) -> EnrichResult:
    """규칙으로 미상인 축을 LLM 으로 보강해 issue_facets 에 upsert(method='llm')."""
    settings = get_settings()
    repo = PostgresIssueRepository()
    rows = await repo.iter_for_classification()

    llm, _mode = _build_classify_llm(settings)
    system = FilePromptRegistry().get(_PROMPT)

    targets = enriched = failed = 0
    for issue_id, jira_key, summary, components, labels in rows:
        base = classify_rule(components, labels, jira_key, summary)
        if not _needs_enrichment(base):
            continue
        targets += 1
        if limit is not None and targets > limit:
            targets -= 1
            break
        try:
            # 제목에 전화번호 등이 섞일 수 있어 LLM 전송 전 마스킹(비파괴).
            user = redact_pii(f"제목: {summary}\n컴포넌트: {', '.join(components) or '-'}")
            raw = _parse_json(await llm.complete(system, user))
            merged = validate_llm_facets(raw, base)
        except Exception as exc:  # LLM/파싱 실패가 배치를 멈추지 않는다(이슈별 격리)
            _logger.warning("classify.enrich_failed", jira_key=jira_key, error=str(exc))
            failed += 1
            continue
        if merged != base:
            await repo.save_facets(issue_id, asdict(merged), method="llm")
            enriched += 1

    _logger.info("classify.enrich.done", targets=targets, enriched=enriched, failed=failed)
    return EnrichResult(targets=targets, enriched=enriched, failed=failed)
