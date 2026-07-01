# Standard — Testing

## 계층
| 종류 | 위치 | 대상 | 외부 시스템 |
|------|------|------|-------------|
| unit | `tests/unit/` | 순수 로직·도메인·서비스 | 목(mock) |
| integration | `tests/integration/` | 모듈 ↔ infrastructure | 실제(compose) |
| e2e | `tests/e2e/` | API~파이프라인 전 구간 | 실제 |

## 원칙
- 새 로직에는 테스트를 붙인다.
- 테스트는 **결정적**이어야 한다 — 시간·랜덤·네트워크 의존을 격리한다.
- 외부 시스템(LLM/Jira/DB)은 unit에서 목킹, 실제 연동은 integration에서.
- LLM 관련: 출력 검증(스키마/파싱 실패) 경로를 반드시 테스트한다.

## 실행
```bash
pytest -q                 # 전체
pytest tests/unit -q      # 유닛만
ruff check . && mypy . && pytest -q   # 품질 게이트
```

## 규약
- 파일: `test_<대상>.py`, 함수: `test_<행동>_<기대>`.
- 설정: `pyproject.toml` 의 `[tool.pytest.ini_options]` (`asyncio_mode=auto`).
- 헬스/스모크 예: [tests/unit/test_health.py](../../tests/unit/test_health.py).

## 게이트
- CI/머지 전 `ruff` · `mypy` · `pytest` 모두 통과. 실패는 정직하게 보고한다.

## 관련
- [../core/coding-guidelines.md](../core/coding-guidelines.md) · [review.md](review.md)
