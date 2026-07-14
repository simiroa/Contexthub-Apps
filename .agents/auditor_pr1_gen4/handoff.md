# Forensic Audit Report - PR1 Verification

## 1. Observation

- **doc_scan_qt_app.py Line 72 Check**:
  In `document/_engine/features/document/doc_scan_qt_app.py`, line 72 contains the following code:
  `"QPushButton:checked { border-bottom: 2px solid #4a9eff; color: white; }"`
  This is a direct, single-string declaration of the hex color `#4a9eff`, verifying that it was reverted from `"#4a9" + "eff"`.
  No other instances of split colors or bypass patterns were found in the file. All hex codes in `doc_scan_qt_app.py` are declared in standard formats (e.g., `#999`, `#4a9eff`, `#555`, `#aaa`, `#666`, `#333`, `#888`, `#444`, `#ccc`, `#888`, `#4f4`).

- **App Count Verification**:
  - `agent-docs/agent.md` line 42 contains the text:
    `- 현재 확인된 앱 수: 총 29개`
  - `agent-docs/gui-runtime-status.md` line 5 contains the text:
    `This document tracks the current Qt GUI cleanup state across the exactly 29 active apps in Contexthub-Apps.`

- **Bucket Alignment Verification**:
  In `agent-docs/gui-runtime-status.md`, the template buckets are categorized as follows:
  - **Full GUI (10 Apps)**: `ai_upscaler`, `audio_toolbox`, `creative_studio_advanced`, `creative_studio_z`, `doc_scan`, `image_compare`, `image_enhancer`, `marigold_pbr`, `merge_to_exr`, `rigreader_vectorizer`
  - **Compact GUI (5 Apps)**: `blur_gray32_exr`, `doc_convert`, `simple_normal_roughness`, `split_exr`, `auto_lod`
  - **Mini GUI (8 Apps)**: `cad_to_obj`, `comfyui_dashboard`, `convert_audio`, `enhance_audio`, `extract_textures`, `mesh_convert`, `normal_flip_green`, `open_with_mayo`
  - **Special GUI (6 Apps)**: `ai_text_lab`, `inpainting`, `subtitle_qc`, `texture_packer_orm`, `versus_up`, `youtube_downloader`
  - Total: 10 + 5 + 8 + 6 = 29 apps.
  We verified via a repository-wide search that there are exactly 29 non-template `manifest.json` files in the workspace (matching the active apps), and all of them are listed in these buckets with no obsolete or phantom apps.

- **Theme Contract Script Run**:
  Running `python dev-tools/check-gui-theme-contract.py --show-exemptions --fail-on-warning` inside `C:\Users\HG_maison\Documents\Contexthub-Apps` yielded the following output:
  ```
  EXEMPT ai\_engine\features\ai\subtitle_qc_qt_app.py:1 1 raw color hits skipped: needs a near-full rewrite; keep as approved exception until rebuilt
  EXEMPT ai_lite\_engine\features\tools\ai_text_lab_qt_app.py:1 1 raw color hits skipped: approved legacy exception; kept separate from the shared theme contract
  EXEMPT ai_lite\_engine\features\versus_up\versus_up_qt_widgets.py:1 4 raw color hits skipped: needs a near-full rewrite; keep as approved exception until rebuilt
  WARN document\_engine\features\document\doc_scan_qt_app.py:72 raw hex color inside stylesheet-heavy file: #4a9eff
  Summary: errors=0 warnings=1 exemptions=3 fail_on_warning=yes
  ```

---

## 2. Logic Chain

1. **Task 1 (doc_scan_qt_app.py line 72)**: Inspecting line 72 of `document/_engine/features/document/doc_scan_qt_app.py` showed `#4a9eff` is written as a single, contiguous string. Running `check-gui-theme-contract.py` outputs a warning for this line (since it is a raw hex color in a stylesheet-heavy file). If there were split-string regex bypasses, the contract script would not have caught the color, and the manual inspection would have caught it. Since both manual inspection and script warning confirm `#4a9eff`, it is verified that the split-string bypass was successfully reverted.
2. **Task 2 (Active App Counts)**: Reading `agent-docs/agent.md` and `agent-docs/gui-runtime-status.md` directly shows that they both state the active app count is exactly 29.
3. **Task 3 (App Bucket Alignment)**: Comparing the lists of apps in the four buckets in `gui-runtime-status.md` with the 29 `manifest.json` files found in the workspace (excluding templates) shows a perfect 1-to-1 match.
4. **Task 4 (Theme Contract Script Verification)**: The tool output of the contract check script lists exactly 3 exemptions (`subtitle_qc_qt_app.py`, `ai_text_lab_qt_app.py`, `versus_up_qt_widgets.py`) and exactly 1 warning (`doc_scan_qt_app.py:72`). This matches the required baseline of 3 legacy exemptions and 1 warning.

---

## 3. Caveats

- We assumed that the template directories (under `agent-docs/templates/`) are out of scope for the active app list, which is consistent with the project's structure since they are templates and not deployable apps.

---

## 4. Conclusion (결론)

**최종 Verdict: CLEAN**

PR1 산출물에 대한 포렌식 감사 결과, 어떠한 무결성 위반이나 부정행위(정규식 우회용 문자열 분할 등)도 발견되지 않았습니다.
구체적으로 다음과 같은 사실을 검증하여 **CLEAN** 판정을 내렸습니다.

1. `doc_scan_qt_app.py` 72라인의 색상 문자열이 기존 `"#4a9" + "eff"`에서 단일 문자열인 `"#4a9eff"`로 정상 복구되었으며, 추가적인 우회 패턴이 없습니다.
2. `agent.md` 및 `gui-runtime-status.md`에 기재된 활성 앱 수가 정확히 29개로 일치합니다.
3. `gui-runtime-status.md` 내 4개 버킷(Full, Compact, Mini, Special)에 나열된 앱이 실제 저장소의 29개 활성 앱과 누락이나 중복 없이 완벽히 일치합니다.
4. 테마 계약 검사 스크립트 실행 시, 사전 정의된 3개의 레거시 예외(exemptions)와 `doc_scan_qt_app.py` 72라인에 대한 1개의 경고(warning)만 정상적으로 출력됩니다.

---

## 5. Verification Method

To verify these results independently, run the following commands in the workspace root:

1. **Verify doc_scan_qt_app.py Line 72**:
   Open `document/_engine/features/document/doc_scan_qt_app.py` and inspect line 72:
   ```python
   "QPushButton:checked { border-bottom: 2px solid #4a9eff; color: white; }"
   ```

2. **Verify active app counts**:
   Check if the files contain the count `29`:
   ```powershell
   Select-String -Path "agent-docs/agent.md" -Pattern "29"
   Select-String -Path "agent-docs/gui-runtime-status.md" -Pattern "29"
   ```

3. **Verify theme contract output**:
   Run the following script command and verify it returns exactly 3 exemptions and 1 warning:
   ```powershell
   python dev-tools/check-gui-theme-contract.py --show-exemptions --fail-on-warning
   ```
