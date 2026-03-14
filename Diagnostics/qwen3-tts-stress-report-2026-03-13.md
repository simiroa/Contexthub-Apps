# Qwen3 TTS Stress Report

## Scope

- Date: 2026-03-13
- Target app: `ai/qwen3_tts`
- Runtime: `C:\Users\HG\miniconda3\envs\contexthub-ai\python.exe`
- GPU: `NVIDIA GeForce RTX 3080 Ti`

## Executed Tests

1. `Preset Voice` single generation
2. `Design New Voice` single generation
3. `Clone from Audio` single generation
4. Mixed batch generation
5. Invalid `Clone from Audio` request without `ref_audio`
6. GUI capture regression

## Outputs

- `Diagnostics/generated/qwen3_stress/01_preset_voice.wav`
- `Diagnostics/generated/qwen3_stress/02_voice_design.wav`
- `Diagnostics/generated/qwen3_stress/03_voice_clone.wav`
- `Diagnostics/generated/qwen3_stress/batch/001_preset.wav`
- `Diagnostics/generated/qwen3_stress/batch/002_design.wav`
- `Diagnostics/generated/qwen3_stress/batch/003_clone_a.wav`
- `Diagnostics/generated/qwen3_stress/batch/004_clone_b.wav`
- `Diagnostics/generated/qwen3_stress/batch/005_preset_ko.wav`

## Result Summary

- All three primary generation modes succeeded on CUDA.
- Mixed batch generation with preset, design, and clone jobs succeeded.
- Two clone jobs with the same reference audio completed in one batch and used the reusable clone prompt path.
- GUI capture succeeded after the latest chat-bubble UI changes.
- Invalid clone input now fails before model load and returns a clear `ref_audio is required for voice_clone mode` error.

## Runtime Fixes Added During Test

- Batch loader now accepts UTF-8 BOM JSON by reading with `utf-8-sig`.
- `voice_clone` now validates `ref_audio` before model load to avoid unnecessary GPU/model startup on invalid input.
- Output saving now avoids silent overwrite by appending `_2`, `_3`, ... when the target file already exists.
- Profile editor now rejects duplicate profile names.

## Observed Risks

### Medium

- SoX is missing in the current environment. The package still generates audio, but every run prints a warning and some future preprocessing paths may rely on it.
- `flash-attn` is not installed. Inference still works, but performance is lower than the recommended CUDA path.
- `hf_xet` is not installed. Hugging Face downloads still work, but first-run model fetch is slower.

### Low

- Progress reporting is job-based, not token-based. This matches the current UX goal, but long single jobs will still appear visually static while running.

## Recommended Follow-up

1. Install `SoX`, `flash-attn`, and `hf_xet` in `contexthub-ai` if faster first-run and cleaner logs are important.
2. Keep clone-profile validation in both UI and runtime to prevent slow invalid launches.
