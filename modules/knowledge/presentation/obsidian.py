"""Knowledge 위키 → Obsidian 마크다운(순수 포매터).

Postgres(진실원천)에서 파생된, 사람이 읽고 편집 가능한 뷰. YAML frontmatter + [[wikilinks]].
비파괴 — 이 모듈은 **문자열만** 만든다(파일 I/O·DB 접근 없음). 조립·쓰기는 apps 계층이 한다.
관련 이슈(issue_related_wiki + body.related_issues)는 `[[JIRA-KEY]]` 위키링크로 이어져
Obsidian 그래프 뷰에서 지식망이 그대로 보인다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from modules.knowledge.application.classification import domain_label
from modules.knowledge.domain.entity import Knowledge

_FACET_TAG_AXES = ("domain", "feature_area", "action", "channel", "issue_type", "team")

_FILENAME_RE = re.compile(r"[^0-9A-Za-z가-힣._-]+")
_JIRA_KEY_RE = re.compile(r"[A-Z][A-Z0-9]+-\d+")
_TAG_RE = re.compile(r"\s+")

_SECTIONS: tuple[tuple[str, str], ...] = (
    ("symptom", "증상"),
    ("root_cause", "근본원인"),
    ("resolution", "해결"),
    ("code_refs", "코드 참조"),
    ("content", "내용"),
)


def jira_key_of(knowledge: Knowledge) -> str | None:
    """sources 의 'issue:<KEY>' 에서 Jira 키를 뽑는다(없으면 None)."""
    for source in knowledge.sources:
        if source.startswith("issue:"):
            return source.removeprefix("issue:")
    return None


def vault_filename(name: str) -> str:
    """Obsidian 노트 파일명으로 안전화한다(경로 구분자/특수문자 제거)."""
    safe = _FILENAME_RE.sub("-", name).strip("-")
    return f"{safe or 'wiki'}.md"


def _safe_segment(name: str) -> str:
    """폴더명으로 안전화(경로 구분자/특수문자 제거)."""
    return _FILENAME_RE.sub("-", name).strip("-") or "미상"


def vault_path(facets: Mapping[str, str], jira_key: str) -> str:
    """facet 기반 저장 경로. 엔진팀(ENG-*) 이슈는 `엔진/<도메인>/` 로 묶고,
    나머지(PA20 등)는 `<도메인>/<기능영역>/<JIRA-KEY>.md`."""
    domain = _safe_segment(domain_label(facets.get("domain", "미상")))
    if jira_key.startswith("ENG-"):  # 엔진팀 이슈는 엔진 폴더로 묶는다
        return f"엔진/{domain}/{vault_filename(jira_key)}"
    feature = _safe_segment(facets.get("feature_area", "미상"))
    return f"{domain}/{feature}/{vault_filename(jira_key)}"


def _verified_topic(sources: Sequence[str]) -> str:
    """검증지식을 주제별 하위폴더로 묶기 위한 분류 — sources 태그 기반(엔진·스케줄러·물류 등)."""
    joined = " ".join(sources)
    if "backend-doc" in sources:
        return "근거-백엔드문서"
    if "notion:스케줄러-배치정리" in sources:
        return "스케줄러"
    if "spec:kctc-logistics" in joined:
        return "KCTC물류"
    if "spec:osse" in joined:
        return "OSSE"
    if "spec:sinsegae-logistics" in joined:
        return "신세계물류"
    if "engine" in sources or "domain:engine" in sources or "spec:coupang-product" in joined:
        return "엔진"
    if "notion:주요기능-주문재고" in sources:
        return "주요기능"
    return "기타"


def standalone_vault_path(knowledge: Knowledge) -> str:
    """이슈에 안 매인 verified 지식의 볼트 경로 — `검증지식/<주제>/<slug>-<id8>.md`.

    Jira 키가 없는 전문가 종합 지식(기능 설명 등)을 도메인 트리 대신 전용 폴더에 두되,
    sources 태그로 주제별(엔진·스케줄러·물류 등) 하위폴더로 묶는다(평평한 mess 방지).
    파일명은 summary 앞부분 slug + id 접두어(안정적·요약 겹쳐도 충돌 회피)."""
    topic = _safe_segment(_verified_topic(knowledge.sources))
    stem = _FILENAME_RE.sub("-", knowledge.summary[:48]).strip("-")
    return f"검증지식/{topic}/{stem or 'wiki'}-{knowledge.id[:8]}.md"


def _yaml_scalar(value: str) -> str:
    """YAML 스칼라를 큰따옴표로 안전하게 감싼다(제목의 '[', ':' 등 대비)."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _as_text(value: object) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def _tag(raw: str) -> str:
    """컴포넌트/신뢰등급을 Obsidian 태그로(공백 제거, 슬래시 네임스페이스)."""
    return _TAG_RE.sub("-", raw.strip())


def _related_links(
    knowledge: Knowledge,
    self_key: str | None,
    related_keys: Sequence[str],
) -> list[str]:
    """issue_related_wiki(외부 주입) + body.related_issues(LLM) 를 합쳐 위키링크 대상 키 목록."""
    body = knowledge.body if isinstance(knowledge.body, dict) else {}
    keys: list[str] = list(related_keys)
    raw = body.get("related_issues")
    if isinstance(raw, (list, tuple)):
        keys.extend(str(item) for item in raw)
    elif isinstance(raw, str):
        keys.extend(_JIRA_KEY_RE.findall(raw))
    # 정규화: 자기 자신 제외 + 순서 보존 dedup
    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        key = key.strip()
        if not key or key == self_key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def to_markdown(
    knowledge: Knowledge,
    *,
    jira_key: str | None = None,
    related_keys: Sequence[str] = (),
    components: Sequence[str] = (),
    facets: Mapping[str, str] | None = None,
) -> str:
    """위키 1건을 Obsidian 마크다운 문자열로 변환한다(frontmatter + 본문 + 관련 위키링크).

    `facets`(ADR-015) 가 주어지면 축별 태그(domain/feature/action/channel/type)를 붙여
    Obsidian 에서 분류축으로 필터·그래프 탐색이 가능하다.
    """
    real_key = jira_key or jira_key_of(knowledge)  # 실제 Jira 키(standalone 이면 None)
    key = real_key or knowledge.id  # frontmatter/자기제외용 안정 식별자
    body = knowledge.body if isinstance(knowledge.body, dict) else {}
    facets = facets or {}

    tags = ["dip/wiki", f"trust/{_tag(knowledge.source)}"]
    tags.extend(f"shelf/{_tag(component)}" for component in components if component.strip())
    for axis in _FACET_TAG_AXES:
        fval = facets.get(axis, "")
        if fval and fval not in ("미상", "공통"):
            tags.append(f"{axis.replace('_', '-')}/{_tag(fval)}")

    front = [
        "---",
        f"id: {knowledge.id}",
        f"jira_key: {_yaml_scalar(key)}",
        f"type: {knowledge.type}",
        f"trust: {knowledge.source}",
        f"created: {knowledge.created_at.isoformat()}",
        f"tags: [{', '.join(tags)}]",
        f"aliases: [{_yaml_scalar(knowledge.summary)}]",
        "---",
    ]

    heading = f"# {real_key} — {knowledge.summary}" if real_key else f"# {knowledge.summary}"
    lines = [heading, ""]
    if facets:
        crumb = " > ".join(
            [
                domain_label(facets.get("domain", "미상")),
                facets.get("feature_area", "미상"),
                facets.get("action", "미상"),
            ]
        )
        lines.append(f"> 분류: {crumb} · 유형: {facets.get('issue_type', '미상')} "
                     f"· 채널: {facets.get('channel', '공통')}")
    lines.append(f"> 신뢰등급: **{knowledge.source}** · 서가: {', '.join(components) or '-'}")
    lines.append("")
    for field, heading in _SECTIONS:
        value = body.get(field)
        text = _as_text(value).strip() if value is not None else ""
        if text:
            lines.append(f"## {heading}")
            lines.append(text)
            lines.append("")

    related = _related_links(knowledge, key, related_keys)
    if related:
        lines.append("## 관련 이슈")
        lines.extend(f"- [[{rk}]]" for rk in related)
        lines.append("")

    return "\n".join(front) + "\n\n" + "\n".join(lines).rstrip() + "\n"


Entry = tuple[str, str, Mapping[str, str]]


def domain_moc_stem(domain_display: str) -> str:
    """도메인 MOC 노트의 파일 stem(= 그래프 노드 이름). 위키링크 `[[stem]]` 대상과 일치해야 한다."""
    return _safe_segment(domain_display)


def _group_by_domain(entries: Sequence[Entry]) -> dict[str, list[Entry]]:
    """엔트리를 도메인 표시명으로 묶는다(정렬 안정성 위해 삽입 순서 보존)."""
    by_domain: dict[str, list[Entry]] = {}
    for entry in entries:
        _key, _summary, facets = entry
        domain = domain_label(facets.get("domain", "미상"))
        by_domain.setdefault(domain, []).append(entry)
    return by_domain


def index_markdown(entries: Sequence[Entry]) -> str:
    """루트 홈 MOC: **도메인 MOC 노트로만** 링크한다.

    그래프에서 index → 도메인(상품·미상 …) → 이슈 로 뻗게 하려면, index 가 이슈를 직접
    링크하면 안 된다(그러면 별 모양). 도메인 MOC 노트를 경유해 계층을 만든다.
    """
    by_domain = _group_by_domain(entries)
    lines = ["---", "tags: [dip/index]", "---", "", "# DIP 지식 도서관", ""]
    lines.append(f"총 {len(entries)}건 · 도메인 {len(by_domain)}개 (분류: 도메인 > 기능영역)")
    lines.append("")
    for domain in sorted(by_domain):
        stem = domain_moc_stem(domain)
        lines.append(f"- [[{stem}]] — {domain} ({len(by_domain[domain])}건)")
    return "\n".join(lines).rstrip() + "\n"


def domain_moc_markdown(domain_display: str, entries: Sequence[Entry]) -> str:
    """도메인 MOC 노트: 해당 도메인 이슈를 **기능영역 헤딩**으로 묶어 `[[KEY]]` 로 링크한다.

    그래프에서 이 노트는 index 와 이슈 사이의 중간 노드가 된다(index → 이 노트 → 이슈).
    """
    features: dict[str, list[tuple[str, str]]] = {}
    for key, summary, facets in entries:
        feature = facets.get("feature_area", "미상")
        features.setdefault(feature, []).append((key, summary))

    lines = ["---", "tags: [dip/moc, dip/domain]", "---", "", f"# {domain_display}", ""]
    lines.append(f"[[index]] · 총 {len(entries)}건 · 기능영역 {len(features)}개")
    lines.append("")
    for feature in sorted(features):
        items = features[feature]
        lines.append(f"## {feature} ({len(items)})")
        lines.extend(f"- [[{key}]] — {summary}" for key, summary in items)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def moc_notes(entries: Sequence[Entry]) -> list[tuple[str, str]]:
    """볼트 홈 계층 노트를 (파일명, 마크다운) 목록으로 만든다.

    반환: `index.md`(루트) + 도메인별 `<도메인>.md`(MOC). 앱은 이걸 볼트 루트에 그대로 쓴다.
    """
    by_domain = _group_by_domain(entries)
    notes: list[tuple[str, str]] = [("index.md", index_markdown(entries))]
    for domain, items in by_domain.items():
        notes.append((vault_filename(domain_moc_stem(domain)), domain_moc_markdown(domain, items)))
    return notes
