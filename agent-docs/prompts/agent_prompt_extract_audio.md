# [P0] AI Agent Task Directive: `extract_audio` Consolidation (Mini/Compact Template)

## 🎯 Task Objective
You are a Feature-Consolidation AI Agent working on the Contexthub-Apps repository. Your mission is to refactor and unify three fragmented audio extraction mini-apps (`extract_audio`, `extract_bgm`, `extract_voice`) into a single, unified app named `extract_audio`. 

## 📚 Mandatory Prerequisites
Before writing or modifying any code, you MUST use the `view_file` or `grep_search` tools to locate and read:
1. `~/.gemini/antigravity/skills/qt-app-builder-contexthub/SKILL.md` (Crucial)
2. `c:\Users\HG\Documents\Contexthub-Apps\agent-docs\agent.md`
3. Identify the main entry points and engines for `extract_audio`, `extract_bgm`, and `extract_voice` (likely in `audio/_engine/features`).

## 🛠 Required Refactoring Steps

1. **Unify Logic (기능 통합)**
   - Instead of maintaining three separated Python/Qt app shells, merge their execution paths into **one** generic `extract_audio_qt_app.py` UI logic.
   - The unified tool should have a simple Mode Selector (e.g., standard `QComboBox` or `SegmentedControl`) exposing three choices: 
     - **"Extract All Audio (Copy)"**
     - **"Isolate Vocal Track (AI)"**
     - **"Isolate Background Music (AI)"**

2. **Establish `mini` (or `compact`) Layout Flow**
   - Use a strictly `mini` or lightweight `compact` layout block.
   - UI should be: **Input (Drop Zone)** -> **Mode Selection** -> **ExportFoldoutCard/Run**.
   - No complex lists or side-panels.

3. **Prune Redundant Apps (사용 안하는 구 앱 삭제 기록)**
   - At the end of your implementation, you must list the exact paths of the redundant folders (`audio/extract_bgm`, `audio/extract_voice`) and their corresponding `_engine` feature entry points that should be safely deleted. (Update `manifest.json` entries appropriately).

4. **Component Conformance (스킬 규칙 준수)**
   - Ensure the new window uses `HeaderSurface`.
   - Remove any custom PySide6 stylesheet injected ad-hoc. Only use `contexthub.ui.qt.shell` palette values.

## ✅ Verification Criteria
- `python c:\Users\HG\Documents\Contexthub-Apps\audio\extract_audio\main.py` opens cleanly.
- Selecting different modes appropriately drives the underlying background service/engine.
- The UI contains no extra bulk or subtitle strings in the header.
