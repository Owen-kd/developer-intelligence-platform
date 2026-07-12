# ADR-016 — Graphify: Neo4j 지식 그래프 + GraphRAG

- 상태: **Accepted** (오너 승인 2026-07-13, "Neo4j ①기반부터"). 1단계(기반+백필) 착수.
- 날짜: 2026-07-13
- 관련: [ADR-003](ADR-003-eventbus.md)(EventBus) · [ADR-015](ADR-015-issue-faceted-taxonomy.md)(facet) · tech-stack(Neo4j 5) · `modules/graph/`(기존 뼈대)

## 맥락
`modules/graph/` 는 뼈대만 있다: 포트(`GraphRepository`: add_node/add_edge/neighbors) + `GraphService`
(`CommitsLinked` → `(:Commit)-[:FIXES]->(:Issue)`). 구현체는 `InMemoryGraphRepository` 뿐이고
`infrastructure/neo4j/` 는 빈 `__init__.py`, 컨테이너(neo4j:5-community)는 정의됐으나 미기동.
즉 그래프에 **위키·facet·컴포넌트가 없고**, 커밋-이슈 엣지만, 인메모리(휘발).

이제 5,080 이슈가 6축 facet + issue_related_wiki + 커밋링크로 **풍부한 관계**를 갖는다. 이걸
실제 그래프로 만들면 "이 이슈와 같은 도메인·채널의 다른 사안", "이 위키 주변 관련 이슈", 다홉 영향 분석이
가능해진다(비전 덱 "AI DevOps Platform" 조각).

## 정직한 트레이드오프 (Neo4j vs Postgres)
**현 규모(5k 이슈)에선 Postgres 재귀 CTE로도 1~2홉 GraphRAG가 가능하다.** facet/related/components가
이미 관계형에 있다. Neo4j의 실익은 **다홉 순회·경로 탐색·코드 의존성 그래프**로 커질 때다(tech-stack 선택).
→ 결론: Neo4j를 **파생 그래프**로 도입하되 **Postgres는 진실 원천 유지**(기존 graph 도메인 docstring과 일치).
과투자 리스크는 "인메모리→Neo4j 어댑터 교체"만으로 최소화하고, GraphRAG 가치를 먼저 소규모로 검증한다.

## 결정 (제안)
1. **새 의존성**: `neo4j`(공식 파이썬 드라이버, async). 근거: 포트-어댑터로 격리, tech-stack 이미 선정.
2. **Neo4jGraphRepository**(`infrastructure/neo4j/`): 기존 `GraphRepository` 포트를 Cypher로 구현
   (MERGE=멱등 노드/엣지, 방향무관 이웃). 설정 `graph_backend`(기본 `memory`, `neo4j` 로 전환).
3. **그래프 모델 확장**(현 Commit-Issue 너머):
   - 노드: `Issue`, `Wiki`, `Commit`, `Domain`, `Channel`, `Component`
   - 엣지: `(Commit)-[:FIXES]->(Issue)`(기존) · `(Wiki)-[:DESCRIBES]->(Issue)` ·
     `(Issue)-[:IN_DOMAIN]->(Domain)` · `(Issue)-[:ON_CHANNEL]->(Channel)` ·
     `(Issue)-[:IN_COMPONENT]->(Component)` · `(Issue)-[:RELATED_TO]->(Wiki)`(issue_related_wiki)
4. **백필**(`apps/graph_backfill.py`): Postgres → Neo4j 로 위 노드/엣지 적재(멱등 MERGE). 진실원천 불변.
5. **자동 배선**: `IssueClassified`(ADR-015) 구독 → 이슈+facet 엣지를 그래프에 반영(상시 최신화).
6. **GraphRAG**(가치): 검색 히트(위키/이슈) → 그래프 이웃 확장("같은 도메인·채널의 관련 사안",
   "관련 위키"). MCP 도구 `graph_neighbors(jira_key)` + (후속) /ask 컨텍스트 보강.

## 대안 비교
1. **Postgres 재귀 CTE GraphRAG**(신규 런타임 0). 현 규모엔 충분·저비용. 그러나 다홉·경로·코드그래프 확장성 약함, tech-stack 이탈.
2. **Neo4j 파생 그래프(채택)**: 순회·시각화(Neo4j Browser)·확장성. 새 런타임/드라이버 비용. Postgres 진실원천 유지로 리스크 억제.
3. **현행 유지(인메모리)**: 휘발·단일프로세스, 상시 서비스 부적합.

## 영향 / 리스크
- **새 런타임+의존성**: 운영 부담↑. compose에 이미 정의된 neo4j 사용, 앱은 포트 뒤 어댑터만.
- **이중 저장(Postgres+Neo4j)**: 동기화 지점 필요 → 백필(1회) + IssueClassified 구독(증분). Neo4j는 재구축 가능한 파생물(유실돼도 백필로 복원).
- **의존성 방향**: 어댑터는 `infrastructure/neo4j`, 모듈은 포트에만 의존(유지).
- **스코프 과대 위험**: 코드파일 노드/파일-이슈 엣지, /ask 그래프 컨텍스트는 **후속**(이번 non-goal).

## 단계 계획 (승인 후)
- **1단계(기반)**: neo4j 드라이버 + `Neo4jGraphRepository`(포트 구현) + 설정 `graph_backend` + docker neo4j 기동 + **백필 스크립트**(Issue/Wiki/Commit/Domain/Channel/Component + 엣지). 검증: Neo4j Browser 순회 쿼리 + 라이브 스모크.
- **2단계(GraphRAG)**: MCP `graph_neighbors(jira_key)` — 같은 도메인·채널 이웃 + 관련 위키. + `IssueClassified` 구독으로 증분 최신화.
- **3단계(후속·non-goal)**: /ask 그래프 컨텍스트 보강 · 코드파일 그래프 · 다홉 영향분석.

## 결과 (승인 시)
- `pyproject`: `neo4j`. `infrastructure/neo4j/graph_repository.py`. `shared/config`: `neo4j_*`/`graph_backend`.
- `apps/graph_backfill.py` + CLI. `apps/mcp` graph_neighbors. 유닛(Cypher 빌더 순수부) + 라이브 스모크.
- 미승인 시: 제안으로 남고 착수 안 함.
