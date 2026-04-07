# [P0] AI Agent Task Directive: `simple_normal_roughness` Standardization (Compact Template)

## 🎯 Task Objective
You are an expert Python/Qt AI Agent working on the Contexthub-Apps repository. Your mission is to refactor the `simple_normal_roughness` app (in the `3d` category folder) to strictly comply with the newly registered `qt-app-builder-contexthub` skill. This app must become the **Golden Reference** for all future `compact` applications.

## 📚 Mandatory Prerequisites
Before writing or modifying any code, you MUST use the `view_file` tool to read:
1. `~/.gemini/antigravity/skills/qt-app-builder-contexthub/SKILL.md` (Crucial)
2. `c:\Users\HG\Documents\Contexthub-Apps\agent-docs\agent.md`
3. Target Feature `c:\Users\HG\Documents\Contexthub-Apps\3d\_engine\features\maps\simple_normal_roughness_qt_app.py` (or similar file name in `3d/_engine/features`).
4. Read what a `compact` template structure should look like in the skill (`assets/templates/compact/` or use standard components like `input_card.py` and `status_card.py`).

## 🛠 Required Refactoring Steps

1. **Establish Strict `compact` Flow (흐름 간소화)**
   - Convert the layout away from wide, multi-column `QSplitter` layouts into a straight, stacked **Single-column** vertical flow.
   - The UX flow should strictly be: 
     **[Input Zone]** -> **[Parameters & Status]** -> **[Real-time Preview]** -> **[Execution Footer]**.

2. **Simplify Input (단일 Input)**
   - If it currently supports complex lists or multiple asset queuing, simplify it to a highly visible single-file Input block (e.g., using a `DropZoneCard` or a simplified `InputCard`).
   - Drag-and-drop should instantly update the preview without forcing a manual selection step.

3. **Status & Real-time Realism (실시간 Preview 중심)**
   - The preview area (`Viewport3DCard` or `ImagePreviewCard`) must occupy the most significant space vertically.
   - Parameter adjustments (like roughness intensity, bump scaling) must immediately trigger preview updates.

4. **Header Rules**
   - Ensure you are using `HeaderSurface` with `show_subtitle=False`.
   - Ensure the window has `attach_size_grip()` because it is non-mini.

5. **Eliminate Raw CSS (기술 부채 해결)**
   - Completely remove any hardcoded Qt stylesheets (`setStyleSheet(...)`). Provide backgrounds and borders exclusively using `get_shell_palette()` metrics and standard Widget roles.

## ✅ Verification Criteria
- `python c:\Users\HG\Documents\Contexthub-Apps\3d\simple_normal_roughness\main.py` opens cleanly.
- The window maintains a strictly single-column `compact` structure (no resizable sidebars).
- Parameter updates properly reflect changes real-time.
