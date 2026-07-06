"""PromptRegistry — 프롬프트 자산을 파일에서 로드한다(코드 인라인 금지).

프롬프트는 프로젝트 자산이다([.ai/core/system.md]). Agent 는 registry 를 통해서만 로드한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from shared.exceptions import NotFoundError

_PROMPTS_ROOT = Path(__file__).resolve().parents[2] / "prompts"


class PromptRegistry(ABC):
    """프롬프트 이름 → 내용 조회 포트."""

    @abstractmethod
    def get(self, name: str) -> str:
        """프롬프트 내용을 반환한다(없으면 NotFoundError)."""


class FilePromptRegistry(PromptRegistry):
    """`prompts/<name>.md` 를 로드하고 캐시한다."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or _PROMPTS_ROOT
        self._cache: dict[str, str] = {}

    def get(self, name: str) -> str:
        if name in self._cache:
            return self._cache[name]
        path = self._root / f"{name}.md"
        if not path.is_file():
            raise NotFoundError(f"프롬프트를 찾을 수 없다: {name} ({path})")
        content = path.read_text(encoding="utf-8")
        self._cache[name] = content
        return content
