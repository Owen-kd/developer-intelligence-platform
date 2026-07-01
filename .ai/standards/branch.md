# Standard — Branch

## 기본
- 기본 브랜치: `main` (항상 배포 가능한 상태 유지).
- 작업은 별도 브랜치에서. `main` 에 직접 커밋하지 않는다.

## 네이밍
```
<type>/<short-summary>
```
| type | 용도 | 예 |
|------|------|----|
| `feature/` | 새 기능 | `feature/jira-collector` |
| `fix/` | 버그 수정 | `fix/health-degraded-status` |
| `chore/` | 잡무/설정 | `chore/ruff-config` |
| `docs/` | 문서 | `docs/ai-operating-system` |
| `refactor/` | 리팩터링 | `refactor/context-builder` |

- 소문자 kebab-case, 요약은 짧고 구체적으로.
- 가능하면 이슈 키를 접미로: `feature/jira-collector-PROJ-12`.

## 수명
- 브랜치는 짧게 유지한다(작은 단위 작업 → 빠른 머지).
- 머지 후 브랜치는 삭제한다.
- 오래된 브랜치는 정기적으로 정리한다.

## 관련
- [commit.md](commit.md) · [pull-request.md](pull-request.md) · [../core/naming-conventions.md](../core/naming-conventions.md)
