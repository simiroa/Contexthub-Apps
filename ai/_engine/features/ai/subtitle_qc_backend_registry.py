from __future__ import annotations

from typing import Dict

from features.ai.subtitle_qc_backend_types import SubtitleGenerationBackend


class SubtitleBackendRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, SubtitleGenerationBackend] = {}

    def register(self, backend: SubtitleGenerationBackend) -> None:
        self._providers[backend.provider_id] = backend

    def get(self, provider_id: str) -> SubtitleGenerationBackend:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise ValueError(f"Unsupported subtitle backend: {provider_id}") from exc

    def ids(self) -> list[str]:
        return sorted(self._providers)


registry = SubtitleBackendRegistry()
