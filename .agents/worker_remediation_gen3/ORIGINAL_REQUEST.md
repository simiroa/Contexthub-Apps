## 2026-07-11T04:25:36+09:00
You are the Gen 3 Remediation Worker.
Working directory: C:\Users\HG_maison\Documents\Contexthub-Apps\.agents\worker_remediation_gen3
Objective: Remediate the integrity violations and documentation mismatches in the repository.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your specific tasks are:
1. Revert the bypass in `document/_engine/features/document/doc_scan_qt_app.py` line 72. Change the split string concatenation back to a single string (from `"#4a9" + "eff"` back to `"#4a9eff"`).
2. Update the total app count to 29 in `agent-docs/agent.md` and `agent-docs/gui-runtime-status.md`.
   - In `agent-docs/agent.md`:
     - Line 34: Change "28개" to "29개".
     - Line 35: Change "28" to "29".
     - Line 42: Change "총 28개" to "총 29개".
   - In `agent-docs/gui-runtime-status.md`:
     - Line 5: Change "exactly 28 active apps" to "exactly 29 active apps".
3. Correct the app buckets in `agent-docs/gui-runtime-status.md`:
   - Remove the 4 obsolete apps: `extract_bgm`, `extract_voice`, `qwen3_tts`, `whisper_subtitle`.
   - Add the 5 active apps: `convert_audio`, `enhance_audio`, `ai_upscaler`, `image_enhancer`, `inpainting`.
   - Place them in the correct categories and update counts in the headers:
     - `### Full GUI (10 Apps)`: Add `ai_upscaler` and `image_enhancer`.
     - `### Mini GUI (8 Apps)`: Remove `extract_bgm` and `extract_voice`, and add `convert_audio` and `enhance_audio`. (Ensure the list is formatted correctly).
     - `### Special GUI (6 Apps)`: Remove `qwen3_tts` and `whisper_subtitle`, and add `inpainting`.
4. Run the theme contract script `python dev-tools/check-gui-theme-contract.py --show-exemptions --fail-on-warning` and confirm the command exit code is 0 and it shows only the 3 legacy exemptions:
   - `ai/_engine/features/ai/subtitle_qc_qt_app.py`
   - `ai_lite/_engine/features/tools/ai_text_lab_qt_app.py`
   - `ai_lite/_engine/features/versus_up/versus_up_qt_widgets.py`
5. Document all changes and command results, and write a completion report to `C:\Users\HG_maison\Documents\Contexthub-Apps\.agents\worker_remediation_gen3\handoff.md`.

Once completed, send a message to the orchestrator (conversation ID: af369a14-cabe-47af-a2f3-671b6a426826) with the path to the handoff file.
