# PR1 Docs Freeze Verification Report

- **Date**: 2026-07-10
- **Verifier**: Empirical Challenger (`challenger_pr1_2_gen2`)
- **Status**: PASSED

## 1. GUI Theme Contract Check

We executed the theme contract checker tool to ensure all active apps adhere to the Qt GUI shared theme guidelines.

### Command
```powershell
python dev-tools/check-gui-theme-contract.py --show-exemptions --fail-on-warning
```

### Output
```
EXEMPT ai_engine\features\ai\subtitle_qc_qt_app.py:1 1 raw color hits skipped: needs a near-full rewrite; keep as approved exception until rebuilt
EXEMPT ai_lite\_engine\features\tools\ai_text_lab_qt_app.py:1 28 raw color hits skipped: approved legacy exception; kept separate from the shared theme contract
EXEMPT ai_lite\_engine\features\versus_up\versus_up_qt_widgets.py:1 4 raw color hits skipped: needs a near-full rewrite; keep as approved exception until rebuilt
Summary: errors=0 warnings=0 exemptions=3 fail_on_warning=yes
```

### Assessment
- **Errors**: 0
- **Warnings**: 0
- **Exemptions**: 3 (All are approved legacy exemptions matching the checker configuration)
- **Result**: PASS

---

## 2. Phantom Component Reference Check

We performed a strict regex-based search for references to the 30 conceptual phantom components (Cards/Workspaces) within the main Qt design documentation files:
1. `agent-docs/qt-component-catalog.md`
2. `agent-docs/gui-runtime-contract.md`

### Regex Query used
```regex
\b(InputCard|PreviewCard|StatusCard|QueueCard|QueueManagerCard|ExecutionCard|FullSplitWorkspace|ImagePreviewCard|AudioPreviewCard|VideoPreviewCard|DocumentPreviewCard|Viewport3DCard|DropZoneCard|BatchListCard|PromptCard|HistoryPanel|PresetSelectorCard|PresetParameterCard|ParameterControlsCard|ModelSelectorCard|ParameterStrip|ExportFoldoutCard|OutputOptionsCard|ProgressStatusBar|DependencyStatusCard|EmptyStateCard|ResultInspectorCard|ToolbarRow|CompareWorkspace|ChannelMapCard)\b
```

### Search Results
- `agent-docs/gui-runtime-contract.md` (Line 78): `- Hub's VideoPreviewCard` (Listed under `Deleted / Banned Components`)
- `agent-docs/qt-component-catalog.md` (Line 85): `- Hub's VideoPreviewCard (Hub 전용 비디오 프리뷰 카드 삭제 및 금지)` (Listed under `Deleted / Banned Components`)

### Assessment
No active/valid components in the documentation refer to any of the 30 phantom components. The only occurrences are under the explicit `Deleted / Banned Components` lists for `VideoPreviewCard`, which is correct and intended.
- **Result**: PASS

---

## 3. Active App Count Verification

We scanned the entire workspace to count all `manifest.json` files and validated the total against the active app list.

### Findings
Total `manifest.json` files found: **30**

#### Excluded Template Directories:
1. `agent-docs/templates/new-app-template/manifest.json`
2. `agent-docs/templates/new-category-template/sample_app/manifest.json`

#### Active Apps List (28 Apps):
1. `3d/auto_lod/manifest.json`
2. `3d/cad_to_obj/manifest.json`
3. `3d/extract_textures/manifest.json`
4. `3d/mesh_convert/manifest.json`
5. `3d/open_with_mayo/manifest.json`
6. `ai/marigold_pbr/manifest.json`
7. `ai/qwen3_tts/manifest.json`
8. `ai/subtitle_qc/manifest.json`
9. `ai/whisper_subtitle/manifest.json`
10. `ai_lite/ai_text_lab/manifest.json`
11. `ai_lite/versus_up/manifest.json`
12. `audio/audio_toolbox/manifest.json`
13. `audio/extract_bgm/manifest.json`
14. `audio/extract_voice/manifest.json`
15. `comfyui/comfyui_dashboard/manifest.json`
16. `comfyui/creative_studio_advanced/manifest.json`
17. `comfyui/creative_studio_z/manifest.json`
18. `document/doc_convert/manifest.json`
19. `document/doc_scan/manifest.json`
20. `image/blur_gray32_exr/manifest.json`
21. `image/image_compare/manifest.json`
22. `image/merge_to_exr/manifest.json`
23. `image/normal_flip_green/manifest.json`
24. `image/rigreader_vectorizer/manifest.json`
25. `image/simple_normal_roughness/manifest.json`
26. `image/split_exr/manifest.json`
27. `image/texture_packer_orm/manifest.json`
28. `utilities/youtube_downloader/manifest.json`

### Documentation Consistency
- `agent-docs/agent.md` lists active app count as: **28** (`현재 확인된 앱 수: 총 28개`)
- `agent-docs/gui-runtime-status.md` lists active app count as: **28** (`This document tracks the current Qt GUI cleanup state across the exactly 28 active apps...`)

Both the physical directories containing `manifest.json` and the documentation files are perfectly aligned.
- **Result**: PASS
