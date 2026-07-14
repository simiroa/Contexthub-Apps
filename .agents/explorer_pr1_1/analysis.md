# Qt GUI API Surface 분석 및 권고 보고서 (Analysis & Recommendations)

## 개요
이 보고서는 `Contexthub-Apps` 저장소의 Qt GUI 디자인 시스템 단순화 계획에 따라, `agent-docs/qt-component-catalog.md` 및 `agent-docs/gui-runtime-contract.md` 문서 내용과 실제 라이브 Qt GUI API 표면(Shared UI 패키지 내 `panels.py` 및 관련 구현체)을 교차 검증한 상세 분석 결과입니다.

---

## 1. 팬텀 컴포넌트 분석 (Phantom Cards/Workspaces/Panels)
`qt-component-catalog.md` 문서에는 개념적으로 정의되어 있으나, 실제 코드(또는 Shared UI 패키지) 내에 PySide6 클래스나 메서드로 구현되어 있지 않은 **팬텀 컴포넌트** 목록은 다음과 같습니다.

### 미구현 개념 카드 및 작업 영역 목록:
1. **Input/Workspace 계열**:
   - `InputCard` (실제 구현 없음)
   - `PreviewCard` (실제 구현 없음)
   - `StatusCard` (실제 구현 없음)
   - `QueueCard` (실제 구현 없음)
   - `QueueManagerCard` (개념만 존재; 실제 코드는 `QueueManagerPanel` 패널 클래스만 존재)
   - `ExecutionCard` (실제 구현 없음)
   - `FullSplitWorkspace` (실제 구현 없음)
2. **도메인 프리뷰 계열**:
   - `ImagePreviewCard` (실제 구현 없음)
   - `AudioPreviewCard` (실제 구현 없음)
   - `VideoPreviewCard` (실제 구현 없음, 또한 Hub의 `VideoPreviewCard`는 호출처가 없어 삭제 예정)
   - `DocumentPreviewCard` (실제 구현 없음)
   - `Viewport3DCard` (실제 구현 없음)
3. **입력/배치 제어 계열**:
   - `DropZoneCard` (실제 구현 없음; 단, `DropListWidget` 헬퍼 클래스는 존재)
   - `BatchListCard` (실제 구현 없음)
   - `PromptCard` (실제 구현 없음)
   - `HistoryPanel` (실제 구현 없음)
   - `PresetSelectorCard` (실제 구현 없음)
   - `PresetParameterCard` (개념만 존재; 실제 코드는 `PresetParameterPanel` 패널 클래스만 존재)
   - `ParameterControlsCard` (개념만 존재; 실제 코드는 `ParameterControlsPanel` 패널 클래스만 존재)
   - `ModelSelectorCard` (실제 구현 없음)
   - `ParameterStrip` (실제 구현 없음)
4. **실행 및 상태 계열**:
   - `ExportFoldoutCard` (개념만 존재; 실제 코드는 `ExportFoldoutPanel` 패널 클래스만 존재)
   - `OutputOptionsCard` (실제 구현 없음)
   - `ProgressStatusBar` (실제 구현 없음)
   - `DependencyStatusCard` (실제 구현 없음)
   - `EmptyStateCard` (실제 구현 없음)
   - `ResultInspectorCard` (개념만 존재; 실제 코드는 `ResultInspectorPanel` 패널 클래스만 존재)
5. **특수 작업 계열**:
   - `ToolbarRow` (실제 구현 없음)
   - `CompareWorkspace` (실제 구현 없음)
   - `ChannelMapCard` (실제 구현 없음)

*참고: `qt-component-catalog.md` 라인 233에 명시된 바와 같이, "나머지 컴포넌트는 개념 카탈로그로 먼저 정의하고, 필요 시 shared runtime으로 점진적으로 승격"하는 정책에 따라 작성되었으나 실제로는 코드가 작성되지 않은 채 문서 부채(Docs Debt)로 남아 있습니다.*

---

## 2. 컴포넌트 실측 분류 및 상태 (Component Classification & Status)
실제 코드베이스 내 호출 빈도와 사용처(callers)를 분석하여 도출한 실제 컴포넌트의 정확한 상태 분류입니다.

### A. 핵심 컴포넌트 (Core Components - 유지 대상)
거의 모든 앱에서 공통 셸 구조를 잡을 때 사용하는 필수 API 및 스타일 헬퍼입니다.
- `build_shell_stylesheet` (약 27개 호출처)
- `HeaderSurface` (약 23개 호출처)
- `apply_app_icon` (약 23개 호출처)
- `attach_size_grip` (약 22개 호출처)
- `get_shell_metrics` (약 26개 호출처)
- `get_shell_palette` (약 17개 호출처)
- `refresh_runtime_preferences` / `runtime_settings_signature` (호환성을 위한 compat stubs, 유지 필요)
- `run_confirm_dialog` / `ConfirmRequest` / `ConfirmChoice` / `ConfirmDialog` (confirm shell 형태의 mini/compact 앱 7개 이상에서 필수적으로 사용)
- `set_surface_role` / `set_button_role` / `set_badge_role` (테마 토큰 바인딩 API, 약 4~6개 호출처)
- `qt_t` (다국어 호환성 헬퍼)

### B. 공통 컴포넌트 (Common Components - 유지 대상)
`full` 또는 `compact` 템플릿의 화면 레이아웃 구성 시 표준으로 쓰이는 패널입니다.
- `ExportFoldoutPanel` (출력 설정 및 진행률 제어, 약 13개 호출처)
- `FixedParameterPanel` (고정 파라미터 입력 양식 구성, 약 12개 호출처)

### C. 선택적 컴포넌트 (Optional Components - 호출처 1개 이상으로 유지 대상)
특정 앱이나 ComfyUI 연동 앱 등에서 제한적으로 사용되나 의존성이 있어 삭제하면 안 되는 컴포넌트 및 헬퍼입니다.
- `PreviewListPanel` (입력 리스트 및 프리뷰 영역, 약 6개 호출처)
- `AssetWorkspacePanel` (Comfy 연동 앱 2개에서 사용)
- `ComparativePreviewWidget` (`image_compare`, `rigreader_vectorizer` 등 2~3개 앱에서 before/after 비교용으로 사용)
- `CollapsibleSection` (접이식 섹션 구성 헬퍼, Comfy 연동 앱 2개에서 사용)
- `ElidedLabel` (`versus_up`, `audio_toolbox` 2개 앱에서 긴 경로 축약용으로 사용)
- `DropListWidget` (`split_channel_qt_app` 등 1개 이상 앱에서 파일 드롭 입력용으로 사용)
- `get_shell_accent_cycle` (accent 색상 순환 헬퍼, `versus_up`, `qwen3_tts` 등 3개 앱에서 사용)
- `set_transparent_surface` (`youtube_downloader` 및 패널 내부에서 투명 표면 지정용으로 사용)

### D. 삭제 예정 컴포넌트 (Scheduled for Deletion - 호출처 0개)
코드베이스 내에 실질적인 사용처(App/Engine caller)가 `0`개로 확인되어 정리 대상(D1)으로 분류된 미사용 패널 및 카드 목록입니다.
- `ExportRunPanel` (호출처 0개, 하단 고정형 `ExportFoldoutPanel`로 단일화 예정)
- `PresetParameterPanel` (호출처 0개, 개별 컴포넌트 조합으로 대체 가능)
- `ParameterControlsPanel` (호출처 0개, 개별 컴포넌트 조합으로 대체 가능)
- `QueueManagerPanel` (호출처 0개, 큐는 개별 관리하도록 변경)
- `ResultInspectorPanel` (호출처 0개, 상세 확인 기능 미사용)
- `VideoPreviewCard` (Hub에만 존재하는 패널이며 호출처 0개, D1 릴리즈 트레인에서 물리 삭제 예정)

---

## 3. template=tag 정책 정의 (template=tag Policy)
`gui-runtime-contract.md`에 명시된 `ui.template` 필드의 의미와 정책적 정의입니다.

- **비-프레임워크 성격 (No functional base class loading)**:
  `ui.template`은 공통 런타임에서 특정 베이스 클래스(예: `BaseFullWindow`)를 자동으로 로드하거나 강제하는 프레임워크 동작이 아닙니다.
- **유지보수 및 인벤토리 태그 역할 (Maintenance Tag)**:
  앱의 레이아웃 성격을 `full`, `compact`, `mini`, `special` 중 하나로 정의하여 저장소 내의 **유지보수 기준 및 인벤토리**를 파악하는 목적으로만 사용됩니다.
- **GUI 캡처 도구와의 연동 (Capture Tooling Consumer)**:
  GUI 자동 캡처 스크립트(`capture-python-gui-apps.ps1`, `gui_capture_launcher.py`)가 각 앱이 어떤 형태로 렌더링되고 실행되어야 하는지 판단하고 캡처 타이밍을 잡기 위해 이 태그를 읽어 들입니다.
- **카테고리별 로컬 분기 허용 (Category-local carving)**:
  예를 들어 `mesh_qt_shared.MeshModeSpec.template`와 같이 카테고리 로컬 수준에서 레이아웃 크기나 위젯 배치를 스위칭하기 위해 예외적으로 template 값을 조회하여 분기할 수 있습니다.
- **개발 레시피 지표**:
  각 태그 유형에 따라 개발자가 조합해야 할 공통 컴포넌트의 표준 구성을 정의합니다 (예: `mini`는 `run_confirm_dialog` 중심 구성, `full`은 `HeaderSurface` + `FixedParameterPanel` + `ExportFoldoutPanel` 조합 권장).

---

## 4. 실행 및 리팩토링 권고 사항
디자인 단순화 및 동기화 불일치를 줄이기 위해 다음의 10단계 PR 로드맵 실행을 제안합니다.

### [Track A: 즉시 실행 가능 단계 (Unblocked)]
- **PR1**: 문서 및 카탈로그 동결. `qt-component-catalog.md`에서 팬텀 카드를 제거하고 실제 라이브 API 표면과 28개 마켓 앱 현황을 반영합니다.
- **PR2**: PR 단위의 theme contract CI 연동. `check-gui-theme-contract.py`를 모든 PR 검사에 태우고, 단순 `*_qt_*.py`만이 아니라 `manifest.json`과 Shared 폴더를 모두 검사 범위로 확장합니다.
- **PR5**: 사용처 0개인 삭제 대상 패널 5종 및 Hub의 `VideoPreviewCard`를 물리적으로 삭제합니다 (Apps-Hub 페어 삭제 적용).
- **PR3-A**: 테마 계약 검사기 확장. `dev-tools/runtime/Shared/` qt 트리를 스캔 범위에 포함하고, 단계적 allowlist(초기에는 `shell.py` 전체 허용)와 삭제된 패널 임포트 금지 룰을 추가합니다.
- **PR8**: 새 앱을 위한 골든 레시피 및 마켓 앱 가이드라인 정리.

### [Track B: 연관 의존성 잠금 해제 단계 (Blocked on Phase 0 - Locked 2026-07-10)]
- **PR6**: 팔레트 수렴. Apps `ShellPalette`를 Hub의 accent `#3A82FF`로 통합하고, `ManualDialog` 및 스타일시트에 산재한 하드코딩 rgba 값을 이 accent 값에서 자동 산출하도록 전환합니다.
- **PR4b**: Apps `shell.py` 모놀리스 분할(extract). 기능 중단 없이 header, theme, widgets 등으로 쪼갭니다.
- **PR7**: Apps-Hub 동기화 드라이런 및 불일치 감지 도구 추가.
- **PR9**: EXEMPT 3종 앱의 하드코딩 스타일시트를 걷어내며 공통 스타일 API 적용.
- **PR10**: `--fail-on-warning` 플래그 활성화로 드리프트 발생 시 즉시 빌드 실패 처리.

---

## 결론 (Conclusion)
이 보고서에서 분석한 Contexthub-Apps의 Qt GUI API 표면 검토 결과, 다음과 같은 결론에 도달하였습니다.

1. **실제 코드와 카탈로그의 괴리 해소**: `qt-component-catalog.md`에 기술된 30여 개의 Card/Workspace 개념은 실제 코드에 구현이 존재하지 않는 문서상의 부채(Phantom Components)이므로, PR1 진행 시 카탈로그에서 이들을 과감히 제거하고 **실제 작동하는 12종의 API 표면 및 recipes**로 명확히 수정해야 합니다.
2. **미사용 컴포넌트 하드 삭제**: `ExportRunPanel`, `PresetParameterPanel` 등 5종의 미사용 패널 및 `VideoPreviewCard`는 실측 호출 빈도가 `0`이므로 PR5 단계에서 Apps와 Hub 양쪽 저장소 모두에서 페어로 삭제 처리를 완료해야 하며, Apps PR 병합 시 해당 Hub 삭제 커밋 SHA를 본문에 기록하는 릴리즈 게이트(K13/K17)를 엄격히 준수하여 동기화 드리프트를 방지해야 합니다.
3. **template=tag 정책 준수**: `ui.template`은 자동 레이아웃 프레임워크가 아닌 단순한 **인벤토리 및 스크린샷 캡처용 태그**이므로, 복잡한 공통 셸 로더나 템플릿 상속 윈도우 클래스(`BaseAppWindow`)를 추가로 설계하지 말고, 현재의 얇은 셸 디자인(Alternative B)을 견고히 유지하면서 테마 검사 CI의 경고 수준을 점진적으로 강화해 나갈 것을 권고합니다.
