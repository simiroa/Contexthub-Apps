# Handoff Report

## 1. Observation
- **Active Apps and Manifests**: 29 active apps are listed in `C:\Users\HG_maison\Documents\Contexthub-Apps\market.json`.
  The search for `manifest.json` on disk (excluding templates) returned exactly 29 paths:
  ```
  3d/auto_lod/manifest.json
  3d/cad_to_obj/manifest.json
  3d/extract_textures/manifest.json
  3d/mesh_convert/manifest.json
  3d/open_with_mayo/manifest.json
  ai/marigold_pbr/manifest.json
  ai/subtitle_qc/manifest.json
  ai_lite/ai_text_lab/manifest.json
  ai_lite/versus_up/manifest.json
  audio/audio_toolbox/manifest.json
  audio/convert_audio/manifest.json
  audio/enhance_audio/manifest.json
  comfyui/ai_upscaler/manifest.json
  comfyui/comfyui_dashboard/manifest.json
  comfyui/creative_studio_advanced/manifest.json
  comfyui/creative_studio_z/manifest.json
  comfyui/image_enhancer/manifest.json
  comfyui/inpainting/manifest.json
  document/doc_convert/manifest.json
  document/doc_scan/manifest.json
  image/blur_gray32_exr/manifest.json
  image/image_compare/manifest.json
  image/merge_to_exr/manifest.json
  image/normal_flip_green/manifest.json
  image/rigreader_vectorizer/manifest.json
  image/simple_normal_roughness/manifest.json
  image/split_exr/manifest.json
  image/texture_packer_orm/manifest.json
  utilities/youtube_downloader/manifest.json
  ```
- **Bypass Removal**: File `C:\Users\HG_maison\Documents\Contexthub-Apps\document\_engine\features\document\doc_scan_qt_app.py` lines 69-74 shows the stylesheet string literal without any string-splitting bypass:
  ```python
  _TAB_STYLE = (
      "QPushButton { background: transparent; border: none; border-bottom: 2px solid transparent; "
      "font-weight: 600; padding: 6px 16px; color: #999; }"
      "QPushButton:checked { border-bottom: 2px solid #4a9eff; color: white; }"
      "QPushButton:disabled { color: #555; }"
  )
  ```
- **Documentation Verification**:
  - `C:\Users\HG_maison\Documents\Contexthub-Apps\agent-docs\agent.md` line 42 states:
    `- 현재 확인된 앱 수: 총 29개`
  - `C:\Users\HG_maison\Documents\Contexthub-Apps\agent-docs\gui-runtime-status.md` line 5 states:
    `This document tracks the current Qt GUI cleanup state across the exactly 29 active apps in Contexthub-Apps.`
    And lists the apps grouped into the following buckets:
    - Full GUI (10 Apps): `ai_upscaler`, `audio_toolbox`, `creative_studio_advanced`, `creative_studio_z`, `doc_scan`, `image_compare`, `image_enhancer`, `marigold_pbr`, `merge_to_exr`, `rigreader_vectorizer`
    - Compact GUI (5 Apps): `blur_gray32_exr`, `doc_convert`, `simple_normal_roughness`, `split_exr`, `auto_lod`
    - Mini GUI (8 Apps): `cad_to_obj`, `comfyui_dashboard`, `convert_audio`, `enhance_audio`, `extract_textures`, `mesh_convert`, `normal_flip_green`, `open_with_mayo`
    - Special GUI (6 Apps): `ai_text_lab`, `inpainting`, `subtitle_qc`, `texture_packer_orm`, `versus_up`, `youtube_downloader`
    These 10 + 5 + 8 + 6 sum up to exactly 29 apps.
- **Theme Contract Checker Output**:
  Running `python dev-tools/check-gui-theme-contract.py --show-exemptions --fail-on-warning` under `C:\Users\HG_maison\Documents\Contexthub-Apps` outputs:
  ```
  EXEMPT ai\_engine\features\ai\subtitle_qc_qt_app.py:1 1 raw color hits skipped: needs a near-full rewrite; keep as approved exception until rebuilt
  EXEMPT ai_lite\_engine\features\tools\ai_text_lab_qt_app.py:1 1 raw color hits skipped: approved legacy exception; kept separate from the shared theme contract
  EXEMPT ai_lite\_engine\features\versus_up\versus_up_qt_widgets.py:1 4 raw color hits skipped: needs a near-full rewrite; keep as approved exception until rebuilt
  WARN document\_engine\features\document\doc_scan_qt_app.py:72 raw hex color inside stylesheet-heavy file: #4a9eff
  Summary: errors=0 warnings=1 exemptions=3 fail_on_warning=yes
  ```

## 2. Logic Chain
- Based on the search for `manifest.json` on disk (excluding templates), we observed 29 active app folders on disk. This is identical to the 29 apps listed in `market.json` (Observation 1).
- Based on inspecting `doc_scan_qt_app.py` line 72, the string concatenation bypass (`"#4a9" + "eff"`) has been replaced by the direct string literal `"#4a9eff"` (Observation 2).
- The documents `agent-docs/agent.md` and `agent-docs/gui-runtime-status.md` explicitly reference the count of exactly 29 apps, and `gui-runtime-status.md` buckets these apps into categories (10 Full, 5 Compact, 8 Mini, 6 Special) which correctly sum to 29 without any duplicates or omissions (Observation 3).
- Running the contract verification tool produces exactly 3 exemptions and 1 warning (on `doc_scan_qt_app.py:72`) as a result of reverting the bypass, matching the verification expectation (Observation 4).
- Therefore, the code and documentation are fully consistent and the bypass has been cleanly resolved.

## 3. Caveats
No caveats.

## 4. Conclusion
### 결론
Contexthub-Apps 저장소 내의 코드와 문서의 일관성을 검증한 결과, 아래와 같이 모든 항목이 완전하게 정합성을 이루고 있음을 확인했습니다.

1. **활성 앱 개수 검증**: `market.json`에 정의된 29개의 앱 목록과 실제 디스크에 존재하는 29개의 개별 앱 폴더(`manifest.json` 기준)가 정확히 일치하며 누락이나 초과가 존재하지 않습니다.
2. **코드 우회(Bypass) 제거 확인**: `document/_engine/features/document/doc_scan_qt_app.py` 72행의 편법적인 문자열 분할 병합 코드(`"#4a9" + "eff"`)가 제거되었으며, 직관적인 `#4a9eff` 리터럴로 환원되었음을 확인하였습니다.
3. **문서 일관성**: `agent-docs/agent.md` 및 `agent-docs/gui-runtime-status.md` 문서 내에 명시된 총 29개의 앱 수량 정보와 4가지 UI 버킷(Full 10개, Compact 5개, Mini 8개, Special 6개) 분류가 상호 정합하며 실제 앱 구성과 완전히 동일합니다.
4. **테마 계약 도구 실행 결과**: `check-gui-theme-contract.py` 스크립트를 `--show-exemptions --fail-on-warning` 플래그와 함께 실행 시, 승인된 예외(Exemptions) 3건과 `doc_scan_qt_app.py` 72행에서의 경고(Warning) 1건만 정상적으로 출력되어 모든 검증 요건을 만족합니다.

## 5. Verification Method
- **App count verification**: Run `python -c "import json, pathlib; print(len([p for p in pathlib.Path().rglob('manifest.json') if 'templates' not in p.parts]))"` to check the manifest file count.
- **Bypass check**: Run `git diff` or inspect `document/_engine/features/document/doc_scan_qt_app.py` line 72.
- **Theme contract tool check**: Run `python dev-tools/check-gui-theme-contract.py --show-exemptions --fail-on-warning` under `C:\Users\HG_maison\Documents\Contexthub-Apps`. It should exit with code 2 and show exactly 3 exemptions and 1 warning.
