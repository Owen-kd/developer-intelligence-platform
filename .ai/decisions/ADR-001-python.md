# ADR-001 — 언어로 Python 3.11+ 채택

- 상태: Accepted
- 날짜: 2026-07-01
- 관련: [ADR-002](ADR-002-fastapi.md)

## 맥락
DIP는 LLM/에이전트, 데이터 파이프라인, 그래프/임베딩 처리를 중심으로 한다.
빠른 반복과 풍부한 AI/데이터 생태계가 필요하다.

## 결정
주 언어로 **Python 3.11+** 를 채택한다.

## 근거
- LLM/ML/데이터 생태계(공식 SDK, 임베딩, 그래프 라이브러리)가 가장 성숙.
- FastAPI/Pydantic/SQLAlchemy 등 async 스택이 견고.
- 3.11+ 의 성능 개선 및 타입 시스템 향상(Self, LiteralString 등).
- 팀 생산성: 프로토타입→운영 전환 비용이 낮다.

## 절충 / 리스크
- 런타임 성능은 Go/Rust보다 낮다 → 병목은 워커 분리/네이티브 확장으로 대응.
- 동적 타입 리스크 → `mypy --strict` + 타입 힌트 필수로 완화.

## 결과
- `requires-python = ">=3.11"` (pyproject).
- 타입 힌트/ruff/mypy를 기본 게이트로 둔다.
