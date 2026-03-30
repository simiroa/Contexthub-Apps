from __future__ import annotations

from pathlib import Path

from features.ai.subtitle_qc_backend_registry import registry
from features.ai.subtitle_qc_backend_types import (
    SubtitleGenerationBackend,
    SubtitleGenerationRequest,
    SubtitleGenerationResult,
)


class CohereTranscribeBackend(SubtitleGenerationBackend):
    provider_id = "cohere"

    def generate(self, request: SubtitleGenerationRequest) -> SubtitleGenerationResult:
        try:
            import torch
            from transformers import pipeline
        except Exception as exc:
            return SubtitleGenerationResult(success=False, error=f"Cohere backend dependencies are unavailable: {exc}")

        model_name = request.model.strip() or "CohereLabs/cohere-transcribe-03-2026"
        try:
            use_cuda = request.device == "cuda" and torch.cuda.is_available()
            device = 0 if use_cuda else -1
            recognizer = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                trust_remote_code=True,
                device=device,
            )
            result = recognizer(str(request.asset_path), return_timestamps=False)
        except Exception as exc:
            return SubtitleGenerationResult(success=False, error=f"Cohere transcription failed: {exc}")

        if isinstance(result, dict):
            text = str(result.get("text", "")).strip()
        else:
            text = str(result).strip()
        if not text:
            return SubtitleGenerationResult(success=False, error="Cohere returned an empty transcript")

        output_paths: list[str] = []
        if "txt" in request.output_formats:
            request.output_dir.mkdir(parents=True, exist_ok=True)
            target = request.output_dir / f"{request.asset_path.stem}.cohere.txt"
            target.write_text(text, encoding="utf-8")
            output_paths.append(str(target))

        return SubtitleGenerationResult(
            success=True,
            segments=[{"start": 0.0, "end": 0.0, "text": text}],
            info={"language": request.language or "auto", "provider": "cohere", "timestamps": False},
            output_paths=output_paths,
        )


registry.register(CohereTranscribeBackend())
