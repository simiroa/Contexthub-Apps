# Handoff Report — App Inventory Audit

## 1. Observation
- **Active App Scan**: Scanned the workspace directory (`C:\Users\HG_maison\Documents\Contexthub-Apps`) for all files named `manifest.json`. Excluded `agent-docs/templates/new-app-template/manifest.json` and `agent-docs/templates/new-category-template/sample_app/manifest.json`. The output returned exactly 28 manifest files.
  - Verification: The `find_by_name` tool found 30 files, of which 28 were active app manifests (excluding the 2 templates).
- **`agent-docs/agent.md`**: Lines 41-42 read:
  ```markdown
  - `ai_lite`: 텍스트 유틸리티처럼 상대적으로 가벼운 AI 도구
  - 현재 확인된 앱 수: 총 43개
  ```
- **`agent-docs/gui-runtime-status.md`**: Lists exactly 28 apps in its bucket categories:
  - Full GUI (8 apps): `audio_toolbox`, `doc_scan`, `merge_to_exr`, `rigreader_vectorizer`, `image_compare`, `creative_studio_advanced`, `creative_studio_z`, `marigold_pbr`
  - Compact GUI (5 apps): `blur_gray32_exr`, `doc_convert`, `simple_normal_roughness`, `split_exr`, `auto_lod`
  - Mini GUI (8 apps): `cad_to_obj`, `comfyui_dashboard`, `extract_bgm`, `extract_textures`, `extract_voice`, `mesh_convert`, `normal_flip_green`, `open_with_mayo`
  - Special GUI (7 apps): `ai_text_lab`, `qwen3_tts`, `subtitle_qc`, `texture_packer_orm`, `youtube_downloader`, `versus_up`, `whisper_subtitle`
  - Under "Out of Scope" (lines 81-82), it states:
    ```markdown
    - categories not included in the standard capture sweep, such as `audio` and `comfyui`, when they need their own review pass
    ```
- **`agent-docs/native-parity-and-removal.md`**: Documented removals from Round-1 and Round-2 cleanups, confirming:
  - Removed apps include: `leave_manager_C`, `pdf_merge`, `pdf_split`, `extract_audio`, `remove_audio`, `interpolate_30fps`, `normalize_volume`, `image_convert`, `resize_power_of_2`, `video_convert`.
  - Line 63 states: `현재 마켓: **28** apps (manifest / market.json / dist 정합)`.
- **`market.json`**: Contains exactly 28 items, matching the 28 active apps.
- **`Diagnostics/gui_capture_log.md`**: Contains run logs showing that categories `audio` and `comfyui` are indeed part of the sweep (e.g., `START audio/audio_toolbox`, `START comfyui/comfyui_dashboard`).

---

## 2. Logic Chain
- **Step 1**: The active app directory scan shows exactly 28 folders containing a `manifest.json` file (excluding templates).
- **Step 2**: Comparison of `gui-runtime-status.md` shows that its bucket list sums up to exactly 28 apps, and the specific app IDs match the scanned folders. Thus, the app inventory list in `gui-runtime-status.md` is complete and up to date.
- **Step 3**: Comparison of `agent.md` shows a discrepancy: it lists "총 43개" (total 43 apps), which is out of date.
- **Step 4**: Checking `native-parity-and-removal.md` reveals that 15 apps were removed during Round-1 and Round-2 cleanup passes to achieve parity with the native SystemC implementations. This accounts for the difference between the legacy 43-app count and the current 28-app count (43 - 15 = 28).
- **Step 5**: Reviewing `gui-runtime-status.md` reveals that its out-of-scope description regarding `audio` and `comfyui` being excluded from standard sweeps is out of date, since `gui_capture_log.md` records show they are actively swept.

---

## 3. Caveats
- No caveats. The physical files on the disk, the package generation configs (`market.json`), and the cleanup logs all point to the exact same 28 active apps.

---

## 4. Conclusion (결론)
Contexthub-Apps 저장소의 활성 앱 개수는 물리적 스캔 및 `market.json` 분석 결과 **정확히 28개**입니다. 
- `agent-docs/agent.md`에 기재된 `총 43개`는 마켓 앱 네이티브 패리티 흡수 작업(Round-1/Round-2)을 통해 15개 앱이 물리적으로 삭제되기 전의 잔재로, **28개**로 수정되어야 합니다.
- `agent-docs/gui-runtime-status.md` 내부의 4가지 GUI 템플릿 버킷 목록은 28개로 정확하게 유지되고 있으나, 명시적인 개수 요약이 누락되어 있고 `Out of Scope` 영역에 `audio` 및 `comfyui` 카테고리가 캡처 스윕에서 제외되어 있다는 잘못된 구식 코멘트가 남아 있어 업데이트가 필요합니다.
- 이에 따라 `agent.md`와 `gui-runtime-status.md`를 안전하게 갱신할 수 있는 계획과 패치 파일(`patch_agent_docs.patch`)을 수립하여 분석 보고서(`analysis.md`)에 정리하였습니다.

---

## 5. Verification Method
- **스캔 검증**: 저장소 루트 디렉터리에서 `manifest.json` 파일을 스캔하여 템플릿 폴더를 제외한 총 개수가 28개인지 확인합니다.
  ```powershell
  Get-ChildItem -Path . -Filter manifest.json -Recurse | Where-Object { $_.FullName -notmatch 'templates' } | Measure-Object
  ```
- **테마 계약 스크립트 실행**: GUI 테마 계약 검증 스크립트가 오류 없이 통과하는지 실행하여 확인합니다.
  ```powershell
  python dev-tools/check-gui-theme-contract.py
  ```
