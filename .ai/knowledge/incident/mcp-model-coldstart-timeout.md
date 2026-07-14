# INCIDENT — MCP `search_wiki` 콜드스타트 타임아웃

> 상태: **해결됨**(재발 방지 배선 + 에러 관측). 최초 발견 2026-07-14.
> 영역: `infrastructure/embedding`, `apps/mcp`. 관련: ADR-009(로컬 임베딩), ADR-013(리랭커).

## 증상
- MCP `search_wiki`(리랭커 경유 하이브리드 검색) 호출이 응답 없이 타임아웃: `MCP error -32001: Request timed out`.
- 재현 조건: 서버 프로세스가 새로 뜬 뒤 **첫 질의**. 두 번째부터는 정상(빠름).

## 근본 원인 (3중 복합)
1. **모델 캐시가 휘발성 `/tmp/fastembed_cache`** — fastembed 기본 캐시가 `/tmp`. 재부팅·OS 정리로 사라지면 다음 로딩 때 모델을 **재다운로드**(e5-large + jina 리랭커 = 약 2.9GB).
2. **리랭커가 무겁고 기본 ON**(`rerank_enabled=True`) — 첫 호출이 임베더(~4.5s) + cross-encoder 리랭커를 함께 로딩. 리랭커 콜드로딩이 병목.
3. **지연 로딩이 '첫 요청' 위에서 실행** — 임베더/리랭커 모두 최초 사용 시 로딩(double-checked lock). MCP 서버에 startup 워밍업이 없어 비용이 **사용자 첫 질의**에 그대로 떨어짐.

실측 콜드스타트 ≈ **70초**(리랭커 파일 재다운로드 63s 포함) → MCP 제한시간 초과.

```
[임베더]  모델적재 3.7s + 첫임베딩 0.2s
[리랭커]  모델적재 66.7s  ← Fetching 5 files (HF 재다운로드)
==> 첫 호출 총 콜드스타트 ≈ 70.6s
```

## 해결 (적용됨)
1. **캐시 영구화** — `Settings.model_cache_dir`를 임베더·리랭커에 `cache_dir`로 전달. `/tmp` 재다운로드 근절. 경로는 OS별 사용자-쓰기가능 위치로 자동 선택(macOS=`~/Library/Caches/dip/fastembed`, Linux=`$XDG_CACHE_HOME`|`~/.cache`). 환경변수 `MODEL_CACHE_DIR`로 override.
   - ⚠️ 주의: 이 머신은 `~/.cache`가 **root 소유**라 사용자 쓰기 불가 → macOS 정식 캐시(`~/Library/Caches`)로 회피. (초기 `~/.cache/dip` 시도가 `Permission denied`로 실패했고, 그 실패가 `embedder.model.load_failed` 로그로 즉시 드러남 — 관측 배선 검증됨.)
2. **startup 워밍업** — `apps/mcp/server.py::main()`이 백그라운드 스레드(`_warmup`)로 모델을 예열. 서버는 즉시 기동, 첫 질의는 warm(≈5s 이하).
3. **에러 관측** — `_ensure_model` 로딩을 구조화 로깅: `*.model.loading` / `*.model.loaded`(elapsed_s) / `*.model.load_failed`(error), 그리고 `mcp.warmup.*`. 실패가 침묵하지 않고 로그에 남는다.

## 탐지 (재발 시 확인할 로그)
- `mcp.warmup.failed error=...` — 워밍업 실패(모델/캐시 문제).
- `embedder.model.load_failed` / `reranker.model.load_failed` — 로딩 실패.
- `*.model.loaded elapsed_s=60+` — 비정상 느린 로딩 → 캐시 유실 의심: `du -sh ~/.cache/dip/fastembed` 확인.

## 선택적 후속
- 검색 지연 더 줄이려면 MCP 경로 `RERANK_ENABLED=false`(하이브리드만, 품질 소폭 tradeoff, 즉시 롤백 가능).
- 설치/배포 시 사전 다운로드: `python -c "from apps.mcp.server import _warmup; _warmup()"` (또는 Docker 빌드 단계).

## 별개 이슈 (검색 품질 — 미해결, 후속 태스크)
- fastembed 경고: `e5-large now uses mean pooling instead of CLS`. **위키 임베딩 시점과 질의 시점의 풀링 방식이 다르면** 벡터 불일치로 검색 정확도 저하 가능.
- 대응 후보: `pyproject.toml`에서 fastembed 버전 고정, 또는 현재 버전 기준 전체 위키 **재임베딩**.
