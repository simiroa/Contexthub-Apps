# [P0] AI Agent Task Directive: `video_convert` Standardization (Full Template)

## 🎯 Task Objective
You are an expert Python/Qt AI Agent working on the Contexthub-Apps repository. Your mission is to refactor the `video_convert` PySide6 app to strictly comply with the newly registered `qt-app-builder-contexthub` skill. This app will serve as the **Golden Reference** for all future `full` template applications.

## 📚 Mandatory Prerequisites
Before writing or modifying any code, you MUST use the `view_file` tool to read:
1. `~/.gemini/antigravity/skills/qt-app-builder-contexthub/SKILL.md` (Crucial component and styling rules)
2. `c:\Users\HG\Documents\Contexthub-Apps\agent-docs\agent.md`
3. `c:\Users\HG\Documents\Contexthub-Apps\video\_engine\features\video\video_convert_qt_app.py` (Target File)
4. Standard component reference files located in `~/.gemini/antigravity/skills/qt-app-builder-contexthub/assets/components/` (e.g., `export_foldout_card.py`, `video_preview_card.py`, `param*`).

## 🛠 Required Refactoring Steps

1. **Header Cleanup (부제목 제거)**
   - In `HeaderSurface`, change `show_subtitle=True` to `show_subtitle=False`. Modern `full` templates should not waste vertical space with long subtitles.
   
2. **Standardize Export UI (출력 UI 기준화)**
   - **DELETE** the custom `ExportRunFoldout` class currently hardcoded inside `video_convert_qt_app.py`.
   - **REPLACE** it by importing and utilizing `export_foldout_card.py` conventions or logic from the standard skill assets, separating the "Run" block gracefully.

3. **Restructure List & Queue Actions (Queue 액션 상단 이동)**
   - Relocate the queue control actions (Add `＋`, Remove `✕`, Clear `Clear`) from the very bottom of the List widget up to the top title row (Header of the list card), which is standard for modern full apps.

4. **Window Resizing & Width Reduction (폭 축소)**
   - The current code hardcodes `self.resize(1480, 960)`. Reduce the default width footprint to around `1080x720` or similar appropriate bounds. The application should not feel excessively wide out of the box. Adjust `QSplitter` stretch ratios.

5. **Eliminate Raw CSS (기술 부채 해결)**
   - Completely delete the `_apply_compact_styles()` method. It contains raw/hardcoded QSS strings (e.g. `border-radius: 12px; background: ...`).
   - All styling must be exclusively derived from the shared `get_shell_palette()` and normal widget roles. 

## ✅ Verification Criteria
- `python c:\Users\HG\Documents\Contexthub-Apps\video\video_convert\main.py` opens cleanly.
- Verify `show_subtitle=False` is active.
- Verify custom raw CSS is entirely eliminated (no `setStyleSheet` blocks using ad-hoc rules).
