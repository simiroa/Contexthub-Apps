## 2026-07-11T04:10:30+09:00

You are a teamwork_preview_worker. Your working directory is C:\Users\HG_maison\Documents\Contexthub-Apps\.agents\worker_remediation_gen2.
Your task is to resolve git divergence and update documentation for PR1 Docs Freeze.

Please follow these exact steps:

### Part 1: Git Alignment
1. Stash all unstaged working directory changes (including doc updates):
   git stash --all
2. Fetch the latest changes from origin:
   git fetch origin
3. Rebase the local commits onto origin/main to integrate the remote's BaseAppWindow implementation while keeping our local commits:
   git rebase origin/main
4. During the rebase, resolve any modify/delete conflicts on deleted market apps (e.g. video_convert, image_convert, resize_power_of_2, pdf_merge, pdf_split, normalize_volume, extract_audio, remove_audio, interpolate_30fps, leave_manager) in favor of deletion:
   git diff --name-only --diff-filter=U | ForEach-Object { git rm $_ }
   git rebase --continue
5. If a conflict occurs on `market.json`, regenerate the registry from active apps, stage it, and resume rebase:
   python .github/scripts/package_apps.py
   git add market.json
   git rebase --continue
6. Apply the stashed changes back:
   git stash pop
7. Resolve any merge conflicts on the 4 documentation files in favor of our local edits (keeping the incoming updates).

### Part 2: Documentation Updates
Apply the following edits to the 4 documents under `agent-docs/`:

1. `agent-docs/agent.md`:
   - Line 42: Update "- 현재 확인된 앱 수: 총 43개" to "- 현재 확인된 앱 수: 총 28개".
   - End of the file: Append "## 9. 공유 런타임 동기화 및 릴리즈 규칙 (Two-Plane SSOT)" as detailed in explorer_pr1_3_gen2/analysis.md.

2. `agent-docs/gui-runtime-contract.md`:
   - Under "Shared Runtime 계약" (lines 53-70): Add "- BaseAppWindow: 공통 Qt GUI 윈도우 베이스 클래스 (창 상태 복원, 핫 리로드 타이머 등 제공)" to the active API list.
   - Under "K2" (Base Class Prohibition Rule): Rename and update to "## K2: Base Class Standardization Rule (공용 윈도우 베이스 클래스 표준화)" and describe standardizing on `BaseAppWindow` rather than prohibiting it, matching the remote codebase implementation (where 17 apps have been migrated to BaseAppWindow).
   - Verify that the "Deleted / Banned Components" section explicitly lists: ExportRunPanel, PresetParameterPanel, ParameterControlsPanel, QueueManagerPanel, ResultInspectorPanel, and Hub's VideoPreviewCard.

3. `agent-docs/gui-runtime-status.md`:
   - Update the "Template Buckets" section (Full GUI, Compact GUI, Mini GUI) to reflect exactly the 28 active apps (8 Full, 5 Compact, 8 Mini, 7 Special) and exclude any removed apps.
   - Under "Current Risks" section, add a point: "- BaseAppWindow alignment: Remote commits have migrated 17 apps to BaseAppWindow to consolidate boilerplate window logic, which is now accepted and standardized in the design documents."

4. `agent-docs/qt-component-catalog.md`:
   - Under "Core Components": Add `BaseAppWindow` with a description of its functions (settings persistence, frameless window flags, mouse drop event handling, preferences reload timing).
   - Under "Deleted / Banned Components": Ensure it lists the 5 deleted panels and Hub's VideoPreviewCard.

### Part 3: Verification
1. Run `python dev-tools/check-gui-theme-contract.py` in the workspace root. Ensure it outputs `errors=0 warnings=0 exemptions=3`.
2. Do not commit or push any changes yet.
3. Write a handoff.md in your working directory C:\Users\HG_maison\Documents\Contexthub-Apps\.agents\worker_remediation_gen2 detailing the git alignment outcome, file changes, and verification command output.
