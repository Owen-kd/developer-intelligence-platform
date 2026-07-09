"""팀별 서가 열람 정책 — 기본 deny, 단일 시행(ADR-010).

정책은 코드가 아니라 설정 파일에서 로드(`config/access/team_shelves.txt`):
    # team: 허용 서가 패턴(ILIKE glob, 콤마 구분)
    commerce: 쿠팡, 상품%, 주문%
    infra: 배포, 인프라%

순수 로직 — DB/외부 접근 없음. 시행(쿼리 필터)은 infrastructure/apps 가 담당한다.
"""

from __future__ import annotations

from pathlib import Path


def load_policies(path: str | Path) -> dict[str, tuple[str, ...]]:
    """정책 파일 → {팀: 허용 서가 패턴들}. 파일 없으면 빈 정책(전원 deny)."""
    file = Path(path)
    if not file.is_file():
        return {}
    policies: dict[str, tuple[str, ...]] = {}
    for line in file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        team, _, rest = stripped.partition(":")
        patterns = tuple(p.strip() for p in rest.split(",") if p.strip())
        if team.strip() and patterns:
            policies[team.strip()] = patterns
    return policies


def allowed_patterns(policies: dict[str, tuple[str, ...]], team: str) -> tuple[str, ...]:
    """팀의 허용 서가 패턴을 반환한다. 정책에 없는 팀은 **빈 튜플(기본 deny)**."""
    return policies.get(team, ())
