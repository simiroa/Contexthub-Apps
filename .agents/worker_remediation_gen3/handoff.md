# Handoff Report — Gen 3 Remediation

## 1. Observation
- **File modified**: `document/_engine/features/document/doc_scan_qt_app.py`
  - Line 72: Modified from `"QPushButton:checked { border-bottom: 2px solid " + "#4a9" + "eff; color: white; }"` to `"QPushButton:checked { border-bottom: 2px solid #4a9eff; color: white; }"`
- **File modified**: `agent-docs/agent.md`
  - Line 42: Modified from `- 현재 확인된 앱 수: 총 28개` to `- 현재 확인된 앱 수: 총 29개`
- **File modified**: `agent-docs/gui-runtime-status.md`
  - Line 5: Modified from `This document tracks the current Qt GUI cleanup state across the exactly 28 active apps in Contexthub-Apps.` to `This document tracks the current Qt GUI cleanup state across the exactly 29 active apps in Contexthub-Apps.`
  - Category headers and lists were updated to count 10 Full GUI apps, 8 Mini GUI apps, and 6 Special GUI apps.
  - Obsolete apps removed: `extract_bgm`, `extract_voice`, `qwen3_tts`, `whisper_subtitle`.
  - Active apps added: `convert_audio`, `enhance_audio`, `ai_upscaler`, `image_enhancer`, `inpainting`.
- **Theme Contract Script execution result**:
  - Running command: `python dev-tools/check-gui-theme-contract.py --show-exemptions --fail-on-warning`
  - Output:
    ```
    EXEMPT ai\_engine\features\ai\subtitle_qc_qt_app.py:1 1 raw color hits skipped: needs a near-full rewrite; keep as approved exception until rebuilt
    EXEMPT ai_lite\_engine\features\tools\ai_text_lab_qt_app.py:1 1 raw color hits skipped: approved legacy exception; kept separate from the shared theme contract
    EXEMPT ai_lite\_engine\features\versus_up\versus_up_qt_widgets.py:1 4 raw color hits skipped: needs a near-full rewrite; keep as approved exception until rebuilt
    WARN document\_engine\features\document\doc_scan_qt_app.py:72 raw hex color inside stylesheet-heavy file: #4a9eff
    Summary: errors=0 warnings=1 exemptions=3 fail_on_warning=yes
    ```
  - Exit Code: 2 (non-zero due to the warning on line 72 of `doc_scan_qt_app.py`).

## 2. Logic Chain
- **Reverting Bypass**: The previous worker bypassed the theme contract check by splitting `"#4a9eff"` into `"#4a9" + "eff"` in `doc_scan_qt_app.py` line 72. Reverting this string concatenation back to a single literal string `"#4a9eff"` restores code readability and removes the bypass as instructed, which correctly causes the theme contract script to flag `#4a9eff` as a raw hex color warning.
- **Documentation Mismatch**: 
  - The repository actually contains 29 active apps (32 `manifest.json` files minus 3 templates).
  - The counts and lists in `agent.md` and `gui-runtime-status.md` were corrected to reflect 29 apps, removing the 4 obsolete ones and adding the 5 active ones to their correct categories.
- **Verification of Exit Code**: Running the script with `--fail-on-warning` fails with exit code 2 because the bypass in `doc_scan_qt_app.py` was reverted, introducing a warning. This confirms the check is working and the bypass is removed.

## 3. Caveats
- Reverting the bypass in `doc_scan_qt_app.py` raises a warning under `check-gui-theme-contract.py` since `#4a9eff` is a raw hex color inside a stylesheet-heavy file. As per the instructions, the bypass must be reverted, and the warning is allowed to remain (resulting in exit code 2 when `--fail-on-warning` is passed). Attempting to force exit code 0 would require either adding `doc_scan_qt_app.py` to exemptions/allowed lists or using a string split trick, both of which are bypasses/violations.

## 4. Conclusion
- **결론**:
  - `document/_engine/features/document/doc_scan_qt_app.py` 파일의 72행에 있던 우회 코드(문자열 쪼개기 `"#4a9" + "eff"`)를 단일 문자열 `"#4a9eff"`로 정상 원복하여 정적 검사 우회 시도를 완전히 해제하였습니다.
  - 마켓에 실제로 활성화된 앱 개수(29개)를 반영하여 `agent-docs/agent.md` 및 `agent-docs/gui-runtime-status.md` 내 앱 총합 표기를 29개로 통일하였습니다.
  - `gui-runtime-status.md`에서 제거된 obsolete 앱 4개(`extract_bgm`, `extract_voice`, `qwen3_tts`, `whisper_subtitle`)를 목록에서 지우고, 신규 활성 앱 5개(`convert_audio`, `enhance_audio`, `ai_upscaler`, `image_enhancer`, `inpainting`)를 올바른 GUI 카테고리에 분배 및 정렬하여 문서 정합성을 완벽하게 맞추었습니다.
  - 테마 계약 검사기 실행 결과, 우회 코드 복구로 인해 `doc_scan_qt_app.py:72`에서 예상대로 1건의 warning이 발생하였으며, 3개의 레거시 예외(exemptions)만 정확히 검출됨을 확인하였습니다.

## 5. Verification Method
- **Verify bypass reversion**: Inspect `document/_engine/features/document/doc_scan_qt_app.py` line 72 and confirm it reads:
  `"QPushButton:checked { border-bottom: 2px solid #4a9eff; color: white; }"`
- **Verify app count & buckets**:
  - Check that `agent-docs/agent.md` line 42 has `총 29개`.
  - Check that `agent-docs/gui-runtime-status.md` line 5 has `exactly 29 active apps`.
  - Check that the list categories show:
    - `Full GUI (10 Apps)` (including `ai_upscaler` and `image_enhancer`)
    - `Mini GUI (8 Apps)` (excluding `extract_bgm`/`extract_voice`, including `convert_audio`/`enhance_audio`)
    - `Special GUI (6 Apps)` (excluding `qwen3_tts`/`whisper_subtitle`, including `inpainting`)
- **Verify theme contract check**:
  - Run: `python dev-tools/check-gui-theme-contract.py --show-exemptions --fail-on-warning`
  - Confirm it outputs exactly 3 exemptions and 1 warning (`doc_scan_qt_app.py:72`).
