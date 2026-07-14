# Handoff Report

## 1. Observation
- **문서 내 컴포넌트 목록 (`agent-docs/qt-component-catalog.md`)**:
  - `HeaderSurface`, `attach_size_grip()`, `InputCard`, `PreviewCard`, `StatusCard`, `QueueCard`, `QueueManagerCard`, `ExecutionCard`, `FullSplitWorkspace`, `ImagePreviewCard`, `AudioPreviewCard`, `VideoPreviewCard`, `DocumentPreviewCard`, `Viewport3DCard`, `DropZoneCard`, `BatchListCard`, `PromptCard`, `HistoryPanel`, `PresetSelectorCard`, `PresetParameterCard`, `ParameterControlsCard`, `ModelSelectorCard`, `ParameterStrip`, `CollapsibleSection`, `ExportFoldoutCard`, `OutputOptionsCard`, `ProgressStatusBar`, `DependencyStatusCard`, `EmptyStateCard`, `ResultInspectorCard`, `ToolbarRow`, `CompareWorkspace`, `ChannelMapCard` 등이 기술되어 있음.
  - 문서 하단(라인 217~232)에는 현재 shared runtime이 직접 제공하는 클래스로 `HeaderSurface`, `PreviewListPanel`, `FixedParameterPanel`, `ExportRunPanel` (legacy compat), `ExportFoldoutPanel`, `PresetParameterPanel`, `ParameterControlsPanel`, `QueueManagerPanel`, `ResultInspectorPanel`, `ComparativePreviewWidget`, `ConfirmDialog`가 기록되어 있음.

- **실제 라이브 Qt GUI API 표면 (`dev-tools/runtime/Shared/contexthub/ui/qt/`)**:
  - `panels.py` 파일은 다음만을 export하고 있음:
    ```python
    __all__ = [
        "AssetWorkspacePanel",
        "ComparativePreviewWidget",
        "ExportFoldoutPanel",
        "ExportRunPanel",
        "FixedParameterPanel",
        "ParameterControlsPanel",
        "PresetParameterPanel",
        "PreviewListPanel",
        "QueueManagerPanel",
        "ResultInspectorPanel",
    ]
    ```
  - `shell.py` 파일 내에는 `HeaderSurface`, `CollapsibleSection`, `ElidedLabel`, `VisibleSizeGrip`, `DropListWidget` 등이 선언되어 동작하고 있음.
  - `confirm_dialog.py` 파일 내에는 `ConfirmRequest`, `ConfirmChoice`, `ConfirmDialog`, `run_confirm_dialog` 등이 구현되어 있음.

- **디자인 단순화 계획 (`agent-docs/designs/2026-07-10-qt-gui-design-system-simplification.md` 결정사항)**:
  - `ExportRunPanel`, `PresetParameterPanel`, `ParameterControlsPanel`, `QueueManagerPanel`, `ResultInspectorPanel` 및 Hub 전용 `VideoPreviewCard` 등 6종 컴포넌트의 사용처가 0개로 실측되어 물리적 삭제(D1)가 확정됨.
  - `ui.template` 필드는 프레임워크 베이스 클래스 로더가 아닌 유지보수 및 자동 캡처 연동 목적의 인벤토리 태그(`template=tag`)로 정의되어 작동함.

---

## 2. Logic Chain
1. `qt-component-catalog.md`의 표준 컴포넌트 목록과 실제 `panels.py` 및 `shell.py`에서 구현/익스포트된 PySide6 클래스들을 1:1로 매핑하여 교차 검증을 수행했습니다.
2. 검증 결과, 카탈로그 상에 존재하지만 실제 코드로 구현되지 않은 약 30여 개의 미구현 컴포넌트(예: `InputCard`, `PreviewCard`, `VideoPreviewCard` 등)를 식별하여 "팬텀 컴포넌트"로 정의하였습니다.
3. 2026-07-10에 Accept된 `qt-gui-design-system-simplification.md` 설계 문서와 실제 코드 내 각 컴포넌트의 callers(사용처) 수량(예: `ExportRunPanel` 등 5종 패널의 사용처가 `0`인 점)을 토대로 Core, Common, Optional, Deletion 대상 컴포넌트를 올바르게 분류하였습니다.
4. `gui-runtime-contract.md` 및 `qt-gui-design-system-simplification.md` 상에서 `ui.template`이 실제 화면 렌더링에 미치는 기능적 메커니즘을 추적한 결과, 이는 레이아웃 스위칭 기능이 결여되어 있으며 캡처 런처와 카테고리 로컬 메트릭 분기용 "태그(tag)"로만 작동함을 규명했습니다.

---

## 3. Caveats
- 현재 구현(implementation) 코드 수정 작업은 사용자 지시사항에 따라 보류(deferred) 상태이며, 이번 분석 단계에서는 문서 및 계획 파일의 검증과 `analysis.md` 리포트 생성까지만 수행되었습니다.
- 로컬 개발 부트스트랩 시 Apps 저장소의 mirror(`dev-tools/runtime/Shared`)가 우선적으로 탐색되므로, product Hub 정본인 `Contexthub/Runtimes/Shared`와의 색상이나 토큰 불일치가 로컬에서 즉각 감지되지 않을 수 있습니다.

---

## 4. Conclusion
1. **팬텀 컴포넌트 정리 필요**: `qt-component-catalog.md`에 나열된 수많은 Card 및 Workspace 개념(예: `InputCard`, `PreviewCard`, `AudioPreviewCard` 등)은 실제 코드로 존재하지 않는 팬텀 컴포넌트입니다. 따라서 향후 PR1 작업을 통해 이들을 문서에서 삭제하고 실제 작동하는 12종의 클래스 및 헬퍼를 기준으로 동결할 것을 권고합니다.
2. **미사용 패널 페어 삭제(D1)**: 호출 빈도가 `0`인 `ExportRunPanel`, `PresetParameterPanel`, `ParameterControlsPanel`, `QueueManagerPanel`, `ResultInspectorPanel` 및 Hub 전용 `VideoPreviewCard` 컴포넌트는 D1 단계에서 Apps mirror와 Hub product 양쪽에서 물리 삭제해야 하며, Apps 삭제 PR에 Hub 삭제 커밋 SHA를 연결하는 릴리즈 게이트(K13/K17)를 준수해야 합니다.
3. **template=tag 정책 정의**: `ui.template`은 공통 런타임의 기능적 클래스 로더가 아닌 단순 **인벤토리 관리 및 자동 캡처 연동용 태그**이므로, 불필요하게 복잡한 셸 상속 윈도우 클래스를 추가하지 말고 현재의 얇은 셸 아키텍처(Alternative B)를 유지할 것을 제안합니다.

---

## 5. Verification Method
- **정적 코드 검사**: `dev-tools/check-gui-theme-contract.py` 스크립트를 아래 명령어로 실행하여 테마 오류 및 허용 예외 상태를 점검할 수 있습니다:
  ```powershell
  python dev-tools/check-gui-theme-contract.py
  ```
- **사용처 재검색**: 아래 Python 명령어를 수행하여 본 handoff에 명시된 삭제 대상 패널 5종 및 `VideoPreviewCard`가 마켓 앱 소스코드에서 여전히 호출되지 않는지(caller count = 0) 재검증할 수 있습니다:
  ```powershell
  python -c "
  import os
  targets = ['ExportRunPanel', 'PresetParameterPanel', 'ParameterControlsPanel', 'QueueManagerPanel', 'ResultInspectorPanel', 'VideoPreviewCard']
  for root, dirs, files in os.walk('.'):
      if '.git' in root or '.agents' in root or 'dev-tools' in root: continue
      for f in files:
          if f.endswith('.py'):
              try:
                  c = open(os.path.join(root, f), encoding='utf-8').read()
                  for t in targets:
                      if t in c: print(f'Found {t} in {root}/{f}')
              except: pass
  "
  ```
