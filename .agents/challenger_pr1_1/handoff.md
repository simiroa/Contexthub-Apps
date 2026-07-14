# Handoff Report

## 1. Observation

1. **API Symbols Coverage Check**:
   - Source document: `agent-docs/qt-component-catalog.md` contains a list of 11 representative classes under the section `## Current Shared Runtime Coverage`:
     - `HeaderSurface`
     - `PreviewListPanel`
     - `FixedParameterPanel`
     - `ExportRunPanel` (legacy compat)
     - `ExportFoldoutPanel`
     - `PresetParameterPanel`
     - `ParameterControlsPanel`
     - `QueueManagerPanel`
     - `ResultInspectorPanel`
     - `ComparativePreviewWidget`
     - `ConfirmDialog`
   - Source codebase: Python files under `dev-tools/runtime/Shared/contexthub/ui/qt/` define these classes as follows:
     - `HeaderSurface` defined in `shell.py`
     - `PreviewListPanel` and `ComparativePreviewWidget` defined in `panels_preview.py`
     - `FixedParameterPanel`, `PresetParameterPanel`, and `ParameterControlsPanel` defined in `panels_parameters.py`
     - `ExportRunPanel` and `ExportFoldoutPanel` defined in `panels_export.py`
     - `QueueManagerPanel` and `ResultInspectorPanel` defined in `panels_status.py`
     - `ConfirmDialog` defined in `confirm_dialog.py`
   - Standard Components Standard Grip:
     - `attach_size_grip` function is defined in `shell.py`.

2. **Active Apps Check**:
   - Source document: `agent-docs/gui-runtime-status.md` lists exactly 28 active apps across four GUI categories (8 Full GUI, 5 Compact GUI, 8 Mini GUI, 7 Special GUI).
   - Source codebase: Scanning `manifest.json` files in the repository, excluding the templates (`agent-docs/templates/new-app-template` and `agent-docs/templates/new-category-template`), results in exactly 28 directories.
   - All 28 app directory names match the active apps listed in `gui-runtime-status.md` exactly, with no discrepancies or extra/missing apps.

3. **App Stability Assets Audit**:
   - Performing a check on the presence of `main.py`, `manual.md`, and an icon (`icon.png` or `icon.ico`) for the 28 active apps revealed that:
     - `document/doc_scan` is missing an icon file.
     - `ai/qwen3_tts` is missing an icon file.
     - All other 26 apps contain all required files.

## 2. Logic Chain

1. **API Symbols**: We parsed the 11 representative classes from `qt-component-catalog.md` and searched the `dev-tools/runtime/Shared/contexthub/ui/qt/*.py` files for matching definitions (`class <name>` and `def <name>`). Every listed symbol was successfully found, indicating that no spelling mistakes or dead exports exist.
2. **App Count**: We collected the set of active apps listed in `gui-runtime-status.md` and compared it against the set of directories containing `manifest.json` (excluding template directories). Both sets contain exactly 28 identical app names, proving perfect alignment.
3. **Asset Verification**: We validated each of the 28 app directories for standard release assets (such as `main.py`, `manual.md`, and an icon). This step uncovered that `doc_scan` and `qwen3_tts` are missing their icons.

## 3. Caveats

- **Package Initialization**: Although the symbols exist within the `contexthub/ui/qt` module files, there is no `__init__.py` in `contexthub/ui/qt`. Thus, these symbols cannot be imported directly from the package level (e.g. `from contexthub.ui.qt import HeaderSurface` is invalid) and must instead be imported from their submodules (e.g., `from contexthub.ui.qt.shell import HeaderSurface`).
- **Conceptual Components**: The standard card components (e.g. `InputCard`, `PreviewCard`, etc.) listed in `qt-component-catalog.md` are documented as conceptual models that are not yet implemented as shared panels, which is consistent with the codebase.

## 4. Conclusion (결론)

1. **API 심볼 일관성**: `qt-component-catalog.md`에 나열된 11개의 실시간(Live) API 심볼은 `contexthub/ui/qt` 패키지 내 각 모듈에 정상적으로 정의되어 있으며 오타나 유효하지 않은 기호는 발견되지 않았습니다. 단, 패키지 루트의 `__init__.py` 파일이 없으므로 모듈 경로를 통해 개별 임포트해야 합니다.
2. **활성 앱 일관성**: `gui-runtime-status.md`에 작성된 28개의 활성 앱은 리포지토리의 실제 `manifest.json` 파일이 포함된 디렉터리와 1:1로 정확하게 일치합니다 (템플릿 제외).
3. **안정성 자산 누락 발견**: 모든 활성 앱에 대해 안정성 요구 자산(`main.py`, `manual.md`, 아이콘)을 전수 조사한 결과, 다음 2개 앱에서 아이콘 파일(`icon.png`/`icon.ico`)이 누락된 상태를 확인했습니다.
   - `document/doc_scan` (아이콘 누락)
   - `ai/qwen3_tts` (아이콘 누락)

## 5. Verification Method

To verify these results independently, run the following Python one-liner in the repository root:

```powershell
python -c "
import pathlib
root = pathlib.Path('.')
# 1. API symbols
lines = root.joinpath('agent-docs/qt-component-catalog.md').read_text(encoding='utf-8').splitlines()
start = 0
for idx, line in enumerate(lines):
    if 'Current Shared Runtime Coverage' in line:
        start = idx
        break
symbols = []
for line in lines[start:]:
    if line.strip().startswith('-'):
        parts = line.split('``')
        if len(parts) > 1:
            symbols.append(parts[1].split()[0])
qt_dir = root.joinpath('dev-tools/runtime/Shared/contexthub/ui/qt')
found = set()
for p in qt_dir.glob('*.py'):
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.startswith('class ') or line.startswith('def '):
            name = line.split()[1].split('(')[0].split(':')[0]
            found.add(name)
missing_api = [s for s in symbols if s not in found]
print('API MISSING:', missing_api)

# 2. Check Apps
status_lines = root.joinpath('agent-docs/gui-runtime-status.md').read_text(encoding='utf-8').splitlines()
listed_apps = set()
in_section = False
for line in status_lines:
    if line.startswith('### '):
        in_section = any(s in line for s in ['Full GUI', 'Compact GUI', 'Mini GUI', 'Special GUI'])
    elif line.startswith('## '):
        in_section = False
    if in_section and line.strip().startswith('-'):
        parts = line.split('``')
        if len(parts) > 1:
            listed_apps.add(parts[1].split()[0])
repo_apps = {p.parent.name for p in root.rglob('manifest.json') if 'agent-docs/templates' not in p.as_posix() and 'dev-tools' not in p.as_posix()}
print('APP LIST MATCHES REPO:', listed_apps == repo_apps)
print('LISTED/REPO COUNT:', len(listed_apps), len(repo_apps))
# 3. Check Icons
for p in root.rglob('manifest.json'):
    if 'agent-docs/templates' not in p.as_posix() and 'dev-tools' not in p.as_posix():
        has_icon = p.parent.joinpath('icon.png').exists() or p.parent.joinpath('icon.ico').exists()
        if not has_icon:
            print('MISSING ICON IN APP:', p.parent.name)
"
```

