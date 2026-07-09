# 24시간 서비스 구동 가이드

> [target-service](../planning/target-service.md) 를 실제로 띄우는 방법. 개인 PC가 아니라 서버 권장.

## 구성요소 (docker compose)
| 서비스 | 역할 | 상시 |
|--------|------|------|
| `postgres`(pgvector) · `redis` · `neo4j` | 저장·벡터·이벤트 큐 | ✅ |
| `api` | `/ask` RAG + 조회 (`:8000`) | ✅ |
| `worker` | 이벤트 소비 → 위키 생성·임베딩·Push (루프2/3) | ✅ |
| `scheduler` | 주기 Jira 수집 → 이벤트 발행 (루프1) | ✅ (기본 OFF) |

앱 3종은 같은 이미지(`Dockerfile`), command 로 역할만 다르다.

## 최초 1회
```bash
cp .env.example .env         # ANTHROPIC_API_KEY / JIRA_* 등 채우기(비우면 Fake 폴백)
docker compose build          # 앱 이미지 빌드
docker compose up -d postgres redis
docker compose run --rm api python -m apps.cli.migrate   # 스키마(009~011) 적용
```

## 상시 구동
```bash
docker compose up -d postgres redis api worker
# 주기 자동수집까지: (APR-002 승인 후) .env 에 SCHEDULER_ENABLED=true → 
docker compose up -d scheduler
```
- 헬스체크: `curl localhost:8000/health`
- 질의: `curl -XPOST localhost:8000/ask -H 'Authorization: Bearer <API_TOKEN>' -H 'Content-Type: application/json' -d '{"question":"쿠팡 옵션 수정 안됨"}'`
- 지식 구멍(되먹임): `GET /ask/gaps`

## 스위치(게이트) — 기본 OFF, 승인 후 .env 로 켠다
| 환경변수 | 효과 | 게이트 |
|----------|------|--------|
| `SCHEDULER_ENABLED=true` | 주기 실 Jira 자동수집 | APR-002 |
| `ACCESS_CONTROL_ENABLED=true` | 팀별 서가 열람 제한(+`DIP_TEAM`) | APR-010 |

## 참고
- fastembed 모델(로컬 임베딩, ~1GB)은 최초 사용 시 `hf_cache` 볼륨에 받아 재사용된다.
- `api` lifespan 은 인메모리 파이프라인을 조립한다(데모). 순수 RAG/이벤트 경로는 Postgres/Redis 를 쓴다.
- 로그: `docker compose logs -f worker`
