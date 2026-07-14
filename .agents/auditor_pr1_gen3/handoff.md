# Handoff Report - PR1 Integrity Verification

## Verdict: INTEGRITY VIOLATION

---

## 1. Observation

We directly observed the following facts and command results:

* **Observation 1 (Cheating / Bypass in Code)**: 
  In `document/_engine/features/document/doc_scan_qt_app.py` line 72, the stylesheet string is written as:
  ```python
  "QPushButton:checked { border-bottom: 2px solid " + "#4a9" + "eff; color: white; }"
  ```
  This split representation concatenates `"#4a9"` and `"eff"`.

* **Observation 2 (Automated Test Check Script)**: 
  In `dev-tools/check-gui-theme-contract.py` line 12, the regular expression for raw hex color detection is defined as:
  ```python
  HEX_COLOR_RE = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b")
  ```
  Because `"#4a9"` does not match the 6-digit length, the script outputs:
  ```
  Summary: errors=0 warnings=0 exemptions=3 fail_on_warning=no
  ```
  completely bypassing the warnings check.

* **Observation 3 (Active App Count and Manifests)**:
  We ran a Python command to verify the manifest count in the repository:
  ```powershell
  python -c "import json, glob; print('market.json entries:', len(json.load(open('market.json')))); print('manifest.json count:', len([p for p in glob.glob('**/manifest.json', recursive=True) if 'templates' not in p]))"
  ```
  *Result*: Both the directories with `manifest.json` (excluding templates) and entries in `market.json` have exactly **29** active apps:
  `auto_lod`, `cad_to_obj`, `extract_textures`, `mesh_convert`, `open_with_mayo`, `marigold_pbr`, `subtitle_qc`, `ai_text_lab`, `versus_up`, `audio_toolbox`, `convert_audio`, `enhance_audio`, `ai_upscaler`, `comfyui_dashboard`, `creative_studio_advanced`, `creative_studio_z`, `image_enhancer`, `inpainting`, `doc_convert`, `doc_scan`, `blur_gray32_exr`, `image_compare`, `merge_to_exr`, `normal_flip_green`, `rigreader_vectorizer`, `simple_normal_roughness`, `split_exr`, `texture_packer_orm`, `youtube_downloader`.

  Running `python .github/scripts/package_apps.py` outputs:
  ```
  Successfully updated market.json with 29 apps.
  ```

* **Observation 4 (Documentation Discrepancies)**:
  * `agent-docs/agent.md` line 42 states: `현재 확인된 앱 수: 총 28개`.
  * `agent-docs/gui-runtime-status.md` line 5 states: `exactly 28 active apps in Contexthub-Apps`.
  * `agent-docs/native-parity-and-removal.md` line 63 states: `현재 마켓: 28 apps (manifest / market.json / dist 정합)`.
  * `agent-docs/gui-runtime-status.md` lists `extract_bgm` (line 55), `extract_voice` (line 57), `qwen3_tts` (line 69), `whisper_subtitle` (line 74) as active apps, but these do not exist in the codebase.
  * `agent-docs/gui-runtime-status.md` fails to list the following 5 active apps: `convert_audio`, `enhance_audio`, `ai_upscaler`, `image_enhancer`, `inpainting`.

* **Observation 5 (K2 and Two-Plane SSOT)**:
  * `agent-docs/gui-runtime-contract.md` documents `K2: Base Class Standardization Rule` standardizing on `BaseAppWindow` (lines 89-93).
  * `agent-docs/gui-runtime-contract.md` documents `Two-Plane SSOT Concept` (lines 95-107).

---

## 2. Logic Chain

1. **Observation 1 & 2** show that the hardcoded hex color `#4a9eff` in `doc_scan_qt_app.py` was split into `"#4a9" + "eff"` to evade the static check script's regular expression. This is an intentional bypass of the theme contract validation checks.
2. **Observation 3 & 4** show that the codebase contains exactly **29** apps (which are registered in `market.json`), but the documentation states there are exactly **28** apps.
3. Furthermore, **Observation 4** shows that `gui-runtime-status.md` lists 4 non-existent (phantom) apps as active and fails to list 5 actual active apps.
4. Therefore, the codebase and documentation are inconsistent, and a validation cheat is present in the source code.

---

## 3. Caveats

No caveats. All checks were performed directly against the local workspace directory, and the packaging and contract validation scripts were executed locally.

---

## 4. Conclusion

**Verdict**: INTEGRITY VIOLATION (무결성 위반)

최종 분석 및 결론:
1. **정적 검사 우회 (우회/치팅)**: `document/_engine/features/document/doc_scan_qt_app.py` 파일의 72번 라인에서 하드코딩된 raw 16진수 색상 코드인 `#4a9eff` 검사를 회피하기 위해 문자열을 쪼개어 합치는 방식(`"#4a9" + "eff"`)을 적용하였습니다. 이는 테마 규격 검사 스크립트(`check-gui-theme-contract.py`)의 정규식을 고의로 우회하려는 부정행위(Cheating)로 판정되어 **INTEGRITY VIOLATION**에 해당합니다.
2. **활성 앱 개수 불일치**: 문서 상으로는 활성 앱 수가 **28개**라고 기재되어 있으나, 실제 디렉터리 내 manifest.json 검색 및 `package_apps.py` 스크립트 실행 결과를 종합하면 실제 활성 앱 수는 **29개**로 불일치가 발생합니다.
3. **문서 일관성 오류 및 유령 컴포넌트(앱) 리스트**: `gui-runtime-status.md` 파일에서 디스크 상에 실존하지 않는 4개의 유령 앱(`extract_bgm`, `extract_voice`, `qwen3_tts`, `whisper_subtitle`)을 활성 상태로 잘못 기재하고 있으며, 실제로 구동 가능한 5개의 앱(`convert_audio`, `enhance_audio`, `ai_upscaler`, `image_enhancer`, `inpainting`)을 누락하여 문서와 코드베이스 간 강한 불일치가 발생합니다.
4. **K2 표준화 규칙 및 Two-Plane SSOT**: `BaseAppWindow` 표준화 내용과 Two-Plane SSOT 관련 사항은 `agent.md` 및 `gui-runtime-contract.md` 문서 내에 정확히 명시되어 있습니다.

이에 따라 PR1 (Docs Freeze) 산출물의 무결성 검증을 통과시킬 수 없으며, 변경사항 반려(Reject)를 권고합니다.

---

## 5. Verification Method

1. **Bypass Verification**:
   Inspect `document/_engine/features/document/doc_scan_qt_app.py` at line 72:
   ```python
   "QPushButton:checked { border-bottom: 2px solid " + "#4a9" + "eff; color: white; }"
   ```
   Compare this against `dev-tools/check-gui-theme-contract.py` line 12 regex.
2. **App Count Verification**:
   Run the following python script to verify actual apps count in the workspace:
   ```powershell
   python -c "import json, glob; print('market.json entries:', len(json.load(open('market.json')))); print('manifest.json count:', len([p for p in glob.glob('**/manifest.json', recursive=True) if 'templates' not in p]))"
   ```
   *Expected actual output*: 29 apps, which conflicts with the 28 apps claimed in `agent.md` and `gui-runtime-status.md`.
3. **Theme Contract Verification**:
   Run the contract check command:
   ```powershell
   python dev-tools/check-gui-theme-contract.py
   ```
   Note that it reports `warnings=0` because of the string-splitting bypass.
