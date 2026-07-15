"""RAG 검색 정확도 평가 하네스 — 회귀 가드.

두 모드:
- `build`: 위키 표본 → LLM(Haiku)으로 구어체 질문 생성 → 골든셋(jsonl) 영속. 1회/갱신 시.
- (기본) `run`: 골든셋을 읽어 실제 검색 파이프라인으로 hit@1/3/5·MRR 측정. LLM 0·결정적.

측정 대상: '검색이 원천 위키를 찾아내는 정확도'(paraphrase 질문). 실사용 커버리지(미수집 지식)
와 답변 합성 충실도는 별도 축. 골든 질문은 파일로 고정 → 변경 전후 회귀 비교 가능.

실행:
    python -m apps.eval_rag build   # 골든셋 생성/갱신
    python -m apps.eval_rag         # 측정
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text

from apps.wiki_pipeline import (
    _build_embedder,
    _build_reranker,
    _build_wiki_llm,
    hybrid_search,
)
from dip_platform.registry import FilePromptRegistry
from infrastructure.postgres import connection as pg
from shared.config.settings import get_settings

GOLDEN_PATH = Path(__file__).resolve().parents[1] / "tests" / "eval" / "golden_qa.jsonl"
_PROMPT = "eval/question_gen"

_SAMPLE = text(
    """
    (SELECT k.id, k.summary, k.source, coalesce(f.domain,'-') dom,
            left(coalesce(k.body->>'symptom','')||' '||coalesce(k.body->>'content',''),400) snip
     FROM knowledge k LEFT JOIN issue_facets f ON f.issue_id=k.issue_id
     WHERE k.type='wiki' AND k.source='derived'
       AND length(coalesce(k.body->>'root_cause',''))>40
     ORDER BY md5(k.id::text) LIMIT :nd)
    UNION ALL
    (SELECT k.id, k.summary, k.source, '-' dom,
            left(coalesce(k.body->>'content',''),400) snip
     FROM knowledge k WHERE k.type='wiki' AND k.source='verified'
     ORDER BY md5(k.id::text) LIMIT :nv)
    """
)


@dataclass(frozen=True)
class GoldenItem:
    id: str
    source: str
    domain: str
    question: str
    summary: str


async def build_golden(n_derived: int = 40, n_verified: int = 20) -> int:
    """위키 표본에서 구어체 질문을 생성해 골든셋(jsonl)으로 저장한다(LLM=Haiku)."""
    settings = get_settings()
    llm, _ = _build_wiki_llm(settings)
    system = FilePromptRegistry().get(_PROMPT)
    async with pg.get_engine().connect() as conn:
        rows = (await conn.execute(_SAMPLE, {"nd": n_derived, "nv": n_verified})).all()

    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with GOLDEN_PATH.open("w", encoding="utf-8") as fh:
        for r in rows:
            user = f"[위키 요약] {r.summary}\n[증상/내용] {r.snip}"
            raw = (await llm.complete(system, user)).strip()
            question = raw.splitlines()[0][:200] if raw else r.summary[:60]
            item = GoldenItem(str(r.id), r.source, r.dom, question, r.summary[:80])
            fh.write(json.dumps(item.__dict__, ensure_ascii=False) + "\n")
            written += 1
    await pg.dispose()
    print(f"골든셋 {written}건 저장 → {GOLDEN_PATH}")
    return written


def _load_golden() -> list[GoldenItem]:
    if not GOLDEN_PATH.is_file():
        raise SystemExit(f"골든셋 없음: {GOLDEN_PATH}. 먼저 `python -m apps.eval_rag build` 실행.")
    items = []
    for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(GoldenItem(**json.loads(line)))
    return items


def _metrics(ranks: list[int]) -> str:
    n = len(ranks) or 1
    h1 = sum(1 for x in ranks if x == 1) / n
    h3 = sum(1 for x in ranks if 1 <= x <= 3) / n
    h5 = sum(1 for x in ranks if 1 <= x <= 5) / n
    mrr = sum(1 / x for x in ranks if x > 0) / n
    return f"hit@1={h1:.0%} hit@3={h3:.0%} hit@5={h5:.0%} MRR={mrr:.2f} (n={len(ranks)})"


async def run_eval() -> None:
    """골든셋을 실제 검색 파이프라인으로 평가한다(LLM 0·결정적)."""
    settings = get_settings()
    embedder = _build_embedder(settings)
    reranker = _build_reranker(settings)
    items = _load_golden()

    ranks: list[int] = []
    by_source: dict[str, list[int]] = {}
    misses: list[str] = []
    for it in items:
        topk, _ = await hybrid_search(it.question, embedder, 5, reranker=reranker)
        ids = [str(kn.id) for kn, _ in topk]
        rank = ids.index(it.id) + 1 if it.id in ids else 0
        ranks.append(rank)
        by_source.setdefault(it.source, []).append(rank)
        if rank == 0:
            misses.append(
                f"    [{it.source}/{it.domain}] Q:{it.question[:40]} → {it.summary[:30]}"
            )

    print("===== RAG 검색 정확도 (회귀 가드) =====")
    print(f"전체     : {_metrics(ranks)}")
    for src in sorted(by_source):
        print(f"{src:8} : {_metrics(by_source[src])}")
    print(f"\ntop5 밖(miss) {len(misses)}건:")
    for m in misses[:15]:
        print(m)
    await pg.dispose()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        asyncio.run(build_golden())
    else:
        asyncio.run(run_eval())


if __name__ == "__main__":
    main()
