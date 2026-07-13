"""중앙 설정. 환경변수(.env)를 단일 소스로 로드한다.

modules/ 는 이 설정을 직접 읽지 않고, infrastructure/ 계층이 사용한다.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "local"
    app_debug: bool = True

    # Auth (내부 도구 최소 모델 — 로컬 기본값. 운영은 시크릿 매니저로 주입)
    api_token: str = "dev-token"

    # LLM (infrastructure 계층에서만 사용. 벤더 기본값=Anthropic — APR-005)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"
    llm_max_tokens: int = 1024
    # Facet LLM 보강(ADR-015 2단계)은 단순 분류라 저가 모델로 충분 — 비용 최소화.
    classify_model: str = "claude-haiku-4-5"
    # 위키 생성 모델·대상(비용 제어, 오너 결정). 기본 Haiku(저가). 빈값이면 anthropic_model 사용.
    wiki_model: str = "claude-haiku-4-5"
    # 이 유형(facet issue_type)만 자동 위키화 — '문의' 등은 스킵(비용↓·품질↑). 콤마 구분.
    wiki_types: str = "오류,기능개선"
    # 이 도메인(facet domain)만 위키화 — 지식화 범위. 확장하려면 도메인 추가(예: stock). 콤마.
    wiki_domains: str = "product,order"

    @property
    def wiki_type_set(self) -> frozenset[str]:
        return frozenset(t.strip() for t in self.wiki_types.split(",") if t.strip())

    @property
    def wiki_domain_set(self) -> frozenset[str]:
        return frozenset(d.strip() for d in self.wiki_domains.split(",") if d.strip())

    # Obsidian 자동 export — 위키 생성 후 볼트를 자동 갱신(비파괴 파생 뷰). 기본 OFF.
    obsidian_auto_export: bool = False
    obsidian_vault_path: str = "vault"

    # Embedding (로컬, infrastructure/embedding 에서만 사용 — ADR-009)
    # 모델 변경 시 embedding_dim 과 009 마이그레이션 vector(N) 을 함께 맞춰야 한다.
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dim: int = 1024

    # Reranker (하이브리드 검색 후 재정렬, 로컬 cross-encoder). 끄면 융합 순위 그대로.
    rerank_enabled: bool = True
    reranker_model: str = "jinaai/jina-reranker-v2-base-multilingual"
    rerank_pool: int = 20  # 2단계 후보 풀(융합 상위 N → 재정렬/다양화 → top-k)

    # 검색 결과 다양화 (MMR — 같은 주제 중복 노출 억제, 비파괴). 끄면 순위 그대로 top-k.
    diversify_enabled: bool = True
    diversify_lambda: float = 0.7  # 1.0=순수 관련도, 0.0=순수 다양성(관련도↔다양성 절충)

    # Jira (infrastructure 계층에서만 사용. 읽기 전용 — APR-002)
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = ""
    jira_max_issues: int = 10  # bounded 수집(최근 N개) — 전량 증분은 후속

    @property
    def jira_configured(self) -> bool:
        return bool(self.jira_base_url and self.jira_email and self.jira_api_token)

    # Git (읽기 전용 로컬 저장소들 — git log 파싱. 콤마로 여러 repo)
    git_repo_paths: str = ""
    git_max_commits: int = 2000  # repo당 bounded 수집(최근 N 커밋)

    @property
    def git_repo_list(self) -> list[str]:
        return [p.strip() for p in self.git_repo_paths.split(",") if p.strip()]

    @property
    def git_configured(self) -> bool:
        return bool(self.git_repo_list)

    # Postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "dip"
    postgres_password: str = "dip"
    postgres_db: str = "dip"

    # Redis (이벤트 브로커 — infrastructure/redis, ADR-011)
    redis_url: str = "redis://localhost:6379/0"

    # Neo4j 지식 그래프 (파생 그래프, 진실원천은 Postgres — ADR-016)
    graph_backend: str = "memory"  # 'memory'(기본) | 'neo4j'
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "dip-neo4j"

    # Scheduler (주기 수집 — apps/scheduler). 기본 비활성(오발 방지). 실 대량수집은 APR-002 승인 후.
    scheduler_enabled: bool = False
    scheduler_interval_seconds: int = 300

    # Access control (팀별 서가 열람 — ADR-010). 기본 OFF(비파괴). 켜는 것은 APR-010 승인 후.
    access_control_enabled: bool = False
    access_policy_file: str = "config/access/team_shelves.txt"
    dip_team: str = ""  # 이 프로세스(MCP 등)의 팀 — 접근제어 켜졌을 때 서가 제한에 사용

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """프로세스당 한 번만 로드되는 설정 싱글턴."""
    return Settings()
