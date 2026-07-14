# PR1 Docs Freeze Verification Report

This report presents the empirical verification results of the PR1 Docs Freeze changes.

---

## 1. GUI Theme Contract Check

We executed the validation script `dev-tools/check-gui-theme-contract.py` to check for theme contract compliance, errors, and warnings:

* **Command**: `python dev-tools/check-gui-theme-contract.py`
* **Result**: `Summary: errors=0 warnings=0 exemptions=3 fail_on_warning=no` (PASS)

We also ran the command with `--show-exemptions` to verify the exemptions:
* **Command**: `python dev-tools/check-gui-theme-contract.py --show-exemptions`
* **Exemptions listed**:
  1. `ai\_engine\features\ai\subtitle_qc_qt_app.py` - approved legacy exception; kept separate from the shared theme contract
  2. `ai_lite\_engine\features\tools\ai_text_lab_qt_app.py` - needs a near-full rewrite; keep as approved exception until rebuilt
  3. `ai_lite\_engine\features\versus_up\versus_up_qt_widgets.py` - needs a near-full rewrite; keep as approved exception until rebuilt

### Adversarial Finding (Bypass of validation script)
* File: `document/_engine/features/document/doc_scan_qt_app.py`
* Line: 72
* Original code: `"QPushButton:checked { border-bottom: 2px solid " + "#4a9" + "eff; color: white; }"`
* **Description**: The hex color `#4a9eff` is split into two separate string literals `"#4a9"` and `"eff"` and concatenated. This prevents the regex `#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b` in `check-gui-theme-contract.py` from matching it, bypassing the raw hex color drift check.

---

## 2. Phantom Component References (Cards/Workspaces)

We checked `agent-docs/qt-component-catalog.md` and `agent-docs/gui-runtime-contract.md` to verify that all references to the 30 conceptual phantom component Cards/Workspaces have been removed.

* **Case-insensitive search for "Card" in `agent-docs/qt-component-catalog.md`**:
  * Only match found: `- Hub's VideoPreviewCard (Hub 전용 비디오 프리뷰 카드 삭제 및 금지)` (Line 117), which is in the "Deleted / Banned Components" section.
* **Case-insensitive search for "Workspace" in `agent-docs/qt-component-catalog.md`**:
  * Only match found: `AssetWorkspacePanel` (Lines 62 and 96), which is a valid live API component.
* **Case-insensitive search for "Card" in `agent-docs/gui-runtime-contract.md`**:
  * Only match found: `- Hub's VideoPreviewCard (Hub-only)` (Line 82), which is in the "Deleted / Banned Components" section.
* **Case-insensitive search for "Workspace" in `agent-docs/gui-runtime-contract.md`**:
  * Only match found: `AssetWorkspacePanel` (Line 65) and generic workspace discussion.
* **Conclusion**: Verified that no active references to the 30 phantom components exist in either document. Only banned components are explicitly listed under the "Deleted / Banned Components" sections.

---

## 3. Active App Count Validation

We verified the number of active directories containing `manifest.json` on disk (excluding template directories under `agent-docs/templates/`) and compared it against the documentation and `market.json`.

* **Active manifest directories found on disk**: **29**
  1. `3d/auto_lod`
  2. `3d/cad_to_obj`
  3. `3d/extract_textures`
  4. `3d/mesh_convert`
  5. `3d/open_with_mayo`
  6. `ai/marigold_pbr`
  7. `ai/subtitle_qc`
  8. `ai_lite/ai_text_lab`
  9. `ai_lite/versus_up`
  10. `audio/audio_toolbox`
  11. `audio/convert_audio`
  12. `audio/enhance_audio`
  13. `comfyui/ai_upscaler`
  14. `comfyui/comfyui_dashboard`
  15. `comfyui/creative_studio_advanced`
  16. `comfyui/creative_studio_z`
  17. `comfyui/image_enhancer`
  18. `comfyui/inpainting`
  19. `document/doc_convert`
  20. `document/doc_scan`
  21. `image/blur_gray32_exr`
  22. `image/image_compare`
  23. `image/merge_to_exr`
  24. `image/normal_flip_green`
  25. `image/rigreader_vectorizer`
  26. `image/simple_normal_roughness`
  27. `image/split_exr`
  28. `image/texture_packer_orm`
  29. `utilities/youtube_downloader`
* **Market Registry Sync**: We ran `python .github/scripts/package_apps.py --check-only` and it succeeded, indicating that `market.json` also has **29** active apps and is in sync.
* **Documentation Discrepancy**:
  * `agent-docs/agent.md` claims there are exactly **28** apps.
  * `agent-docs/gui-runtime-status.md` claims there are exactly **28** active apps.
  * Mismatched lists in `gui-runtime-status.md`:
    * Lists 4 non-existent app directories: `extract_bgm`, `extract_voice`, `qwen3_tts`, `whisper_subtitle`.
    * Omits 5 existing app directories: `convert_audio`, `enhance_audio`, `ai_upscaler`, `image_enhancer`, `inpainting`.
* **Conclusion**: The active app count on disk is **29**, not 28. The documentation is out of sync and needs correction to reflect the true set of active apps.

---

## 4. Git Merge/Rebase Conflicts Check

We checked if there are any git rebase or merge conflicts left in the repository.

* **Command**: `git diff --name-only --diff-filter=U`
* **Result**: No conflicted files in the git index.
* **Grep Search for conflict markers**: No occurrences of `<<<<<<<` found.
* **Conclusion**: Verified that no git merge/rebase conflicts exist in the repository.

---

## 5. 결론 (Conclusion)

### 요약 및 검증 결과

1. **테마 계약 스크립트 검증**: `check-gui-theme-contract.py` 실행 결과 에러와 경고가 모두 0개(예외 3개)로 성공적으로 통과하였습니다. 단, `doc_scan_qt_app.py` 72라인에서 16진수 색상 검사를 우회하기 위해 문자열을 쪼개어 합치는 편법이 사용된 것을 확인하였습니다.
2. **유령 컴포넌트 제거 검증**: `qt-component-catalog.md` 및 `gui-runtime-contract.md` 파일에서 30개의 유령 컴포넌트(Cards/Workspaces)에 대한 활성화된 참조는 모두 제거되었습니다. 삭제/금지된 컴포넌트는 오직 "Deleted / Banned Components" 섹션 하위에만 명시되어 있습니다.
3. **활성 앱 개수 검증 (오류 발견)**: 실제 디스크 상에서 `manifest.json`을 포함하고 있는 활성 앱 디렉터리는 총 **29개**입니다 (`market.json`과 일치). 하지만 문서(`agent.md` 및 `gui-runtime-status.md`)에서는 활성 앱 수를 **28개**로 표기하고 있으며, 현재는 디스크에 존재하지 않는 앱(4개)을 포함하고 실제 존재하는 앱(5개)을 누락하는 불일치가 발생해 문서가 최신화되지 않은 상태입니다.
4. **Git 충돌 검증**: 레포지토리에 git rebase/merge 충돌 및 충돌 마커(`<<<<<<<`)가 존재하지 않음을 성공적으로 확인하였습니다.
