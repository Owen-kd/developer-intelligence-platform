"""상시 Worker — Redis 이벤트 소비 → 루프2 지식화 + 루프3-Push(ADR-011, target-service).

scheduler(생산자)가 발행한 IssueCreated 를 Redis 로 받아, 이 프로세스가:
- 루프2: 자동 위키 생성·임베딩(WikiAutoGenerator) 💰 이슈당 1회
- 루프3-Push: 유사 과거 위키 자동 연결(RelatedKnowledgePush) — 내부 저장(Jira 쓰기는 게이트)

실행:
    docker compose up -d
    python -m apps.worker.run        # 상시 소비 루프(Ctrl-C 로 종료)
"""

from __future__ import annotations

import asyncio

from apps.wiki_pipeline import (
    RelatedKnowledgePush,
    WikiAutoGenerator,
    _build_embedder,
    _build_llm,
)
from dip_platform.registry import FilePromptRegistry
from infrastructure.postgres import connection as pg
from infrastructure.postgres.event_store import PostgresEventStore
from infrastructure.redis.event_bus import RedisEventBus
from modules.knowledge.application.wiki_service import WikiGenerationService
from modules.knowledge.infrastructure.repository import (
    PostgresIssueSourceReader,
    PostgresKnowledgeRepository,
)
from shared.config.settings import get_settings
from shared.logger import get_logger

_logger = get_logger("apps.worker")


def build_worker_bus() -> RedisEventBus:
    """Redis 버스 + 루프2/루프3-Push 구독자를 조립한다(구독은 생성자에서 등록)."""
    settings = get_settings()
    bus = RedisEventBus(settings.redis_url, store=PostgresEventStore())

    reader = PostgresIssueSourceReader()
    repo = PostgresKnowledgeRepository()
    embedder = _build_embedder(settings)
    llm, _mode = _build_llm(settings)
    service = WikiGenerationService(llm, FilePromptRegistry(), repo)

    WikiAutoGenerator(service, reader, repo, embedder, bus)  # 루프2
    RelatedKnowledgePush(reader, repo, embedder, bus)  # 루프3-Push
    return bus


async def _main() -> None:
    bus = build_worker_bus()
    _logger.info("worker.starting")
    try:
        await bus.run()  # 상시 소비 루프
    finally:
        await bus.aclose()
        await pg.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
