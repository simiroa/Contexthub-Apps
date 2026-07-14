# PR1 Docs Freeze Remediation Plan

This remediation plan synthesizes the findings from the Forensic Auditor (`auditor_pr1/handoff.md`) and Reviewer 1 (`reviewer_pr1_1/review_report.md`) to resolve documentation contradictions and sync the local repository branch `main` with the remote `origin/main`.

---

## 1. Git Alignment Steps to Sync with origin/main

The local branch `main` and `origin/main` have diverged. The remote branch `origin/main` contains 25 commits not in local `main` (including the implementation of `BaseAppWindow` and app refactoring), while local `main` has 3 commits (removing market apps to sync with SystemC). In addition, there are unstaged modifications in the working directory.

To align both branches while preserving the market app deletions and local documentation additions, perform the following steps:

```bash
# Step 1: Stash all unstaged working directory changes (including doc updates)
git stash --all

# Step 2: Fetch the latest changes from origin
git fetch origin

# Step 3: Rebase the local commits onto origin/main
# This integrates the remote's BaseAppWindow implementation while keeping our local commits
git rebase origin/main
```

### Handling Rebase Conflicts

During the rebase, modify/delete conflicts will occur on files belonging to the deleted market apps (e.g., `video_convert`, `image_convert`, `resize_power_of_2`, `pdf_merge`, `pdf_split`, `normalize_volume`, `extract_audio`, `remove_audio`, `interpolate_30fps`, `leave_manager`).
These apps have been absorbed into SystemC, so the deletions must be preserved.

Run the following commands to resolve conflicts in favor of deletion:

```bash
# Automate resolving all modify/delete conflicts by removing the deleted files
git diff --name-only --diff-filter=U | ForEach-Object { git rm $_ }

# Resume the rebase
git rebase --continue
```

If a conflict occurs on `market.json`, resolve it by regenerating the file from the current active app folders:

```bash
# Regenerate market.json using the packaging script
python .github/scripts/package_apps.py

# Stage the updated market.json and continue
git add market.json
git rebase --continue
```

```bash
# Step 4: Apply the stashed changes back to the working directory
git stash pop
```
If minor merge conflicts occur on the 4 documentation files during the stash pop, resolve them in favor of our local edits, incorporating the remote reality of `BaseAppWindow` as described below.

---

## 2. Exact Edits to the 4 Documents

To resolve the "BaseAppWindow" conflict, update the app count to 28, clean up the deleted panels, and document the Two-Plane SSOT/Release Gate, apply the following exact edits to the 4 documents in `agent-docs/`.

### File 1: `agent-docs/agent.md`

#### Edit A: Update the total app count to 28
- **Location**: Line 42
- **Action**: Replace `총 43개` with `총 28개`.

```markdown
<<<<
- 현재 확인된 앱 수: 총 43개
====
- 현재 확인된 앱 수: 총 28개
>>>>
```

#### Edit B: Append Section 9 for Two-Plane SSOT and K13 Release Gate
- **Location**: End of the file (Line 80 onwards)
- **Action**: Append the Two-Plane SSOT concept and Release Gate policy.

```markdown
<<<<
- 공유 런타임을 수정했다면 `Contexthub\Runtimes\Shared` 원본 반영 여부까지 확인한다.
====
- 공유 런타임을 수정했다면 `Contexthub\Runtimes\Shared` 원본 반영 여부까지 확인한다.

## 9. 공유 런타임 동기화 및 릴리즈 규칙 (Two-Plane SSOT)

공유 런타임(Shared Runtime) 소스 코드의 동기화 및 릴리즈 구조는 다음 **Two-Plane SSOT (단일 진실 공급원)** 개념을 철저히 따른다.

1. **Product Shared runtime original** = `Hub Runtimes/Shared`
   - 실제 서비스 환경에서 구동되는 프로덕션 런타임 소스의 원본(Original)이다.
2. **Dev Shared mirror original** = Apps `dev-tools/runtime/Shared`
   - 앱 개발 환경 및 패키징 시 검증에 사용되는 개발용 미러 원본(Mirror Original)이다.
3. **Market ZIP never contains Shared runtime code.**
   - 배포 마켓에 업로드되는 각 개별 앱의 ZIP 파일은 어떠한 경우에도 Shared runtime 코드를 내장하거나 포함해서는 안 된다. Shared runtime은 플랫폼 서비스(Hub)에서 공통으로 로드하고 제공한다.
4. **Release Gate (K13) requirement:**
   - 임의로 `dev-tools/runtime/Shared` 코드를 수정하여 배포해서는 안 된다. Shared runtime의 동작이나 코드를 변경할 때는 반드시 **연관된 Hub의 커밋/PR을 명시하거나 동기화(sync) 계획**을 함께 릴리즈 게이트 문서에 기재해야 한다.
>>>>
```

---

### File 2: `agent-docs/gui-runtime-contract.md`

#### Edit A: Add BaseAppWindow to active Shared Runtime 계약 (API surface)
- **Location**: Lines 53-70 (Shared Runtime 계약 section)
- **Action**: Add `BaseAppWindow` to the active API list.

```markdown
<<<<
- `HeaderSurface`: 앱 상단 헤더
- `PreviewListPanel`: 입력 목록과 미리보기 영역
====
- `HeaderSurface`: 앱 상단 헤더
- `PreviewListPanel`: 입력 목록과 미리보기 영역
- `BaseAppWindow`: 공통 Qt GUI 윈도우 베이스 클래스 (창 상태 복원, 핫 리로드 타이머 등 제공)
>>>>
```

#### Edit B: Revise K2 Base Class Prohibition to Base Class Standardization
- **Location**: "K2: Base Class Prohibition Rule" section
- **Action**: Rename and update the description to accept and standardize on `BaseAppWindow`.

```markdown
<<<<
## K2: Base Class Prohibition Rule

- **Prohibit shared BaseAppWindow / template base classes globally across all application tiers.**
- 모든 애플리케이션 계층에서 공통 `BaseAppWindow`나 템플릿 기반의 공유 base class 사용을 완전히 금지한다.
- 각 앱은 런타임에서 로드되는 표준 윈도우 클래스를 가지거나 독립적으로 윈도우를 작성해야 하며, 상속을 통한 암묵적인 레이아웃 공유나 기능 공유 패턴을 배제하여 강한 결합을 원천 차단한다.
====
## K2: Base Class Standardization Rule (공용 윈도우 베이스 클래스 표준화)

- **Standardize on `BaseAppWindow` for Qt GUI application windows to consolidate settings persistence, frameless window flags, custom icon handling, and runtime preferences reload timing.**
- 공통 `BaseAppWindow`를 표준으로 도입하여 창 상태/위치 복원(`QSettings`), 프레임리스 윈도우 플래그, 마우스 드롭 이벤트 처리, 테마/설정 핫 리로드 타이머 등 공통 보일러플레이트 로직을 통합 관리한다.
- 개별 앱에서의 불필요한 보일러플레이트 중복 코드를 제거하고 강한 결합을 방지하기 위해 공용 런타임 내 표준 `BaseAppWindow`를 상속하여 구현하는 것을 권장한다. (이미 17개 앱이 `BaseAppWindow`를 상속받는 구조로 리팩토링 및 통합이 완료됨)
>>>>
```

#### Edit C: Ensure Deleted/Banned Components are correct
- **Location**: "Deleted / Banned Components" section
- **Action**: Ensure the deleted panels match the 5 banned components exactly.

```markdown
## Deleted / Banned Components

다음 컴포넌트 및 패널은 삭제/금지되었으며, 어떠한 앱에서도 사용하거나 참조할 수 없다.

- `ExportRunPanel`
- `PresetParameterPanel`
- `ParameterControlsPanel`
- `QueueManagerPanel`
- `ResultInspectorPanel`
- Hub's `VideoPreviewCard`
```

---

### File 3: `agent-docs/gui-runtime-status.md`

#### Edit A: Update Template Buckets to reflect 28 apps
- **Location**: Lines 20-75 (Template Buckets section)
- **Action**: Update list of manifested apps under each bucket to match the 28 apps exactly.

```markdown
<<<<
### Full GUI

Apps that use the shared Qt shell plus dense panels, previews, and long-form parameter blocks.

Manifested apps:

- `audio_toolbox`
- `doc_scan`
- `merge_to_exr`
- `resize_power_of_2`
- `rigreader_vectorizer`
- `video_convert`
- `image_compare`
- `creative_studio_advanced`
- `creative_studio_z`
- `marigold_pbr`

### Compact GUI

Apps with no multi-input list, only one main preview-or-list surface, and a small set of immediately understandable options.

Manifested apps:

- `blur_gray32_exr`
- `doc_convert`
- `pdf_merge`
- `simple_normal_roughness`
- `split_exr`
- `auto_lod`

### Mini GUI

Small confirm-shell windows with very few options and selection-summary style input.

Manifested apps:

- `cad_to_obj`
- `comfyui_dashboard`
- `extract_audio`
- `extract_bgm`
- `extract_textures`
- `extract_voice`
- `image_convert`
- `interpolate_30fps`
- `mesh_convert`
- `normalize_volume`
- `normal_flip_green`
- `open_with_mayo`
- `pdf_split`
- `remove_audio`
====
### Full GUI

Apps that use the shared Qt shell plus dense panels, previews, and long-form parameter blocks.

Manifested apps (8 apps):

- `audio_toolbox`
- `doc_scan`
- `merge_to_exr`
- `rigreader_vectorizer`
- `image_compare`
- `creative_studio_advanced`
- `creative_studio_z`
- `marigold_pbr`

### Compact GUI

Apps with no multi-input list, only one main preview-or-list surface, and a small set of immediately understandable options.

Manifested apps (5 apps):

- `blur_gray32_exr`
- `doc_convert`
- `simple_normal_roughness`
- `split_exr`
- `auto_lod`

### Mini GUI

Small confirm-shell windows with very few options and selection-summary style input.

Manifested apps (8 apps):

- `cad_to_obj`
- `comfyui_dashboard`
- `extract_bgm`
- `extract_textures`
- `extract_voice`
- `mesh_convert`
- `normal_flip_green`
- `open_with_mayo`
>>>>
```

#### Edit B: Document BaseAppWindow integration under Current Risks
- **Location**: "Current Risks" section
- **Action**: Add a point explaining that the `BaseAppWindow` remote codebase integration is now aligned with documentation.

```markdown
<<<<
- `ui.template` should be filled on the apps we consider structurally special so the bucket is declared in manifest, not inferred from file names.
====
- `ui.template` should be filled on the apps we consider structurally special so the bucket is declared in manifest, not inferred from file names.
- **BaseAppWindow alignment**: Remote commits have migrated 17 apps to `BaseAppWindow` to consolidate boilerplate window logic, which is now accepted and standardized in the design documents.
>>>>
```

---

### File 4: `agent-docs/qt-component-catalog.md`

#### Edit A: Remove Phantom Components and insert BaseAppWindow under Core Components
- **Location**: Lines 40-174 (rewritten to "Live API Surface Components")
- **Action**: Insert `BaseAppWindow` under Core Components.

```markdown
<<<<
### Core Components

- `build_shell_stylesheet()`
- `HeaderSurface`
- `apply_app_icon()`
- `attach_size_grip()`
- `get_shell_metrics()`
- `get_shell_palette()`
- `refresh_runtime_preferences()`
- `runtime_settings_signature()`
- `run_confirm_dialog()`
- `set_surface_role()` / `set_button_role()` / `set_badge_role()`
- `qt_t`
====
### Core Components

- `build_shell_stylesheet()`
- `HeaderSurface`
- `apply_app_icon()`
- `attach_size_grip()`
- `get_shell_metrics()`
- `get_shell_palette()`
- `refresh_runtime_preferences()`
- `runtime_settings_signature()`
- `run_confirm_dialog()`
- `set_surface_role()` / `set_button_role()` / `set_badge_role()`
- `qt_t`
- `BaseAppWindow`
  - 공통 Qt GUI 윈도우 베이스 클래스 (`shared/_engine/runtime/base_window.py`에 정의). 창 상태/위치 복원(`QSettings`), 프레임리스 윈도우 플래그, 마우스 드롭 이벤트 처리, 테마/설정 핫 리로드 타이머 등 공통 보일러플레이트 로직을 수행함.
>>>>
```

#### Edit B: Document Deleted / Banned Components
- **Location**: "Deleted / Banned Components" section
- **Action**: Ensure the deleted panels match the 5 banned components.

```markdown
## Deleted / Banned Components

다음 패널 및 컴포넌트는 복잡성을 줄이고 시스템을 단순화하기 위해 **완전히 삭제되었으며 사용이 금지(Banned)**되어 있다.
앱 구현 시 이 컴포넌트들을 참조하거나 사용해서는 안 된다.

- `ExportRunPanel` (Legacy compat 레이어 삭제)
- `PresetParameterPanel` (preset과 parameter를 복합 구성하는 패널 삭제)
- `ParameterControlsPanel` (독립 파라미터 컨트롤 패널 삭제)
- `QueueManagerPanel` (대기열 관리 패널 삭제)
- `ResultInspectorPanel` (실행 결과 검사 패널 삭제)
- Hub's `VideoPreviewCard` (Hub 전용 비디오 프리뷰 카드 삭제 및 금지)
```
