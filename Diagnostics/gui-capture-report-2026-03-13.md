# GUI Capture Report (2026-03-13)

## Scope

- Repository: `Contexthub-Apps`
- Shared runtime source used for test: `dev-tools/runtime/Shared`
- Test mode: `CTX_HEADLESS=1`, `CTX_CAPTURE_MODE=1`
- Python used: `python` on local machine

## Why this setup

앱 코드의 런타임 경로를 직접 수정하지 않고, 테스트 런처가 공유 런타임 경로를 주입하는 방식으로 검증했다. 이 방식은 실제 배포 구조를 보존하면서도 저장소 내부에서 반복 테스트가 가능하다.

## Result Summary

### Captured successfully

- `image/image_compare`
- `image/image_convert`
- `image/image_metadata`
- `image/merge_to_exr`
- `image/resize_power_of_2`
- `image/rigreader_vectorizer`
- `image/split_exr`
- `ai/demucs_stems`
- `ai/esrgan_upscale`
- `ai/marigold_pbr`
- `ai/rmbg_background`
- `ai/whisper_subtitle`
- `ai_light/ai_text_lab`
- `ai_light/prompt_master`
- `document/doc_convert`
- `document/doc_scan`
- `document/pdf_merge`
- `document/pdf_split`

### Skipped by current filter

이 항목들은 현재 캡처 스크립트 기준으로 Python GUI 앱이 아닌 것으로 분류되어 건너뛰었다.

- `image/normal_flip_green`
- `image/simple_normal_roughness`
- `image/texture_packer_orm`

## Important Interpretation

- 이번 검증은 "창이 실제로 열리는가"를 본 GUI 부트 검증이다.
- AI 카테고리 앱도 현재 환경에서 GUI는 정상 기동했다.
- 다만 모델 다운로드, 실제 추론, 외부 바이너리 호출, 긴 작업 흐름까지 검증한 것은 아니다.
- 따라서 `ai` 카테고리는 "GUI 기동 성공, 기능 완전 검증 아님"으로 기록하는 것이 정확하다.

## Output Locations

- Log: `Diagnostics/gui_capture_log.md`
- Screenshots:
  - `Diagnostics/gui_captures/image/*.png`
  - `Diagnostics/gui_captures/ai/*.png`
  - `Diagnostics/gui_captures/ai_light/*.png`
- Process logs: `Diagnostics/gui_captures/logs/*`

## Notable Details

- `ai_light/ai_text_lab` stdout에는 `Deep-Translator initialized` 로그가 남았다.
- 이번 실행에서 생성된 stderr 로그는 대상 앱 전반에서 비어 있었다.
- `image/resize_power_of_2`는 개별 실행과 전체 캡처 배치 모두에서 정상 캡처되었다.
- 후속 수정 후 `esrgan_upscale`, `whisper_subtitle`, `rmbg_background`는 하단 실행 버튼과 진행 바가 첫 화면에 노출되도록 재검증했다.
- `doc_scan`은 `BaseWindow` 전환 후에도 정상 캡처되었다.

## Suggested Manual Wording

앱 매뉴얼이나 개발 문서에는 아래 수준으로 적는 편이 적절하다.

- `GUI launch verified locally on 2026-03-13 using local shared runtime mirror.`
- `AI category apps passed GUI boot capture, but model execution and external tool workflows were not part of this check.`
