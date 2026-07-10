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
    """facet 기반 저장 경로 `<도메인>/<기능영역>/<JIRA-KEY>.md` (도메인>기능영역 조직화)."""
    domain = _safe_segment(domain_label(facets.get("domain", "미상")))
    feature = _safe_segment(facets.get("feature_area", "미상"))
    return f"{domain}/{feature}/{vault_filename(jira_key)}"


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
    key = jira_key or jira_key_of(knowledge) or knowledge.id
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

    lines = [f"# {key} — {knowledge.summary}", ""]
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


def index_markdown(entries: Sequence[tuple[str, str, Mapping[str, str]]]) -> str:
    """홈 MOC 노트: (jira_key, summary, facets) 를 **도메인 > 기능영역** 으로 묶어 링크한다."""
    # {도메인표시명: {기능영역: [(key, summary)]}}
    tree: dict[str, dict[str, list[tuple[str, str]]]] = {}
    for key, summary, facets in entries:
        domain = domain_label(facets.get("domain", "미상"))
        feature = facets.get("feature_area", "미상")
        tree.setdefault(domain, {}).setdefault(feature, []).append((key, summary))

    lines = ["---", "tags: [dip/index]", "---", "", "# DIP 지식 도서관", ""]
    lines.append(f"총 {len(entries)}건 · 도메인 {len(tree)}개 (분류: 도메인 > 기능영역)")
    lines.append("")
    for domain in sorted(tree):
        features = tree[domain]
        total = sum(len(v) for v in features.values())
        lines.append(f"## {domain} ({total})")
        for feature in sorted(features):
            items = features[feature]
            lines.append(f"### {feature} ({len(items)})")
            lines.extend(f"- [[{key}]] — {summary}" for key, summary in items)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
