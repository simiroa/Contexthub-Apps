from __future__ import annotations

from features.ai.subtitle_qc_backend_registry import registry
from features.ai.subtitle_qc_backend_types import (
    SubtitleGenerationBackend,
    SubtitleGenerationRequest,
    SubtitleGenerationResult,
)


class WhisperSubtitleBackend(SubtitleGenerationBackend):
    provider_id = "whisper"

    def generate(self, request: SubtitleGenerationRequest) -> SubtitleGenerationResult:
        from features.ai.standalone.subtitle_gen import generate_subtitles

        result = generate_subtitles(
            str(request.asset_path),
            model_size=request.model,
            device=request.device,
            task=request.task,
            language=request.language,
            output_formats=request.output_formats,
            output_dir=str(request.output_dir),
            return_result=True,
        )
        if not isinstance(result, dict):
            return SubtitleGenerationResult(success=False, error="Unknown generation result")
        return SubtitleGenerationResult(
            success=bool(result.get("success")),
            segments=list(result.get("segments", [])),
            info=dict(result.get("info") or {}),
            output_paths=list(result.get("output_paths", [])),
            error=str(result.get("error", "")),
        )


registry.register(WhisperSubtitleBackend())
