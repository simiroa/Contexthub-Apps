# Qt Component Catalog

이 문서는 `Contexthub-Apps`의 Qt 앱을 앱 단위 템플릿만이 아니라 컴포넌트 조합 단위로 정리하기 위한 기준 카탈로그다.

## Why

현재 shared runtime에는 공통 shell과 일부 panel이 있지만, 새 앱 작성 시 여전히 앱 단위 복제 의존이 크다.
이를 줄이기 위해 앱은 아래 두 층으로 본다.

1. 템플릿 버킷 (ui.template 태그)
   - `mini`
   - `compact`
   - `full`
   - `special`
2. 표준 컴포넌트 (실제 존재)
   - Core components (API)
   - Common components
   - Optional components

## Live API Surface Components

실제 codebase에 존재하고 동작하는 라이브 API surface 컴포넌트 목록이다. 이외의 개념적인 phantom 컴포넌트들은 사용되지 않으며 구현되어 있지 않다.

### Core Components

- `build_shell_stylesheet()`
  - 쉘의 스타일시트를 생성하고 적용하는 핵심 함수.
- `HeaderSurface`
  - 앱 상단의 공통 헤더. 앱 이름 + 아이콘 버튼만 사용하며, 부제목, open 버튼, 상태 배지는 기본값에서 숨김.
- `apply_app_icon()`
  - 앱 윈도우에 공통 앱 아이콘을 설정하는 함수.
- `attach_size_grip()`
  - 윈도우 우측 하단에 크기 조절 그립(size grip)을 부착하는 함수. `mini`를 제외한 공통 규칙.
- `get_shell_metrics()`
  - 여백, 버튼 높이, 미리보기 높이, 헤더 높이 등의 레이아웃 단위를 가져오는 함수.
- `get_shell_palette()`
  - 테마 색상과 표면 배경 값(palette)을 가져오는 함수.
- `refresh_runtime_preferences()`
  - 런타임 환경설정을 갱신하고 반영하는 함수.
- `runtime_settings_signature()`
  - 런타임 환경설정의 유효성을 검증하는 시그니처 함수.
- `run_confirm_dialog()`
  - 확인 및 확인 다이얼로그(Confirm Dialog)를 실행하는 공통 함수.
- `set_surface_role()` / `set_button_role()` / `set_badge_role()`
  - 위젯이나 버튼, 배지에 특정 표면/스타일 역할을 지정하는 스타일 헬퍼 함수.
- `qt_t`
  - 다국어 번역을 위한 번역 함수.
- `BaseAppWindow`
  - 공통 Qt GUI 윈도우 베이스 클래스 (`shared/_engine/runtime/base_window.py`에 정의). 창 상태/위치 복원(`QSettings`), 프레임리스 윈도우 플래그, 마우스 드롭 이벤트 처리, 테마/설정 핫 리로드 타이머 등 공통 보일러플레이트 로직을 수행함.

### Common Components

- `ExportFoldoutPanel`
  - 하단 고정 액션 행을 가진 접이식(foldout) 내보내기 패널.
- `FixedParameterPanel`
  - 화면에 고정된 형태의 파라미터 조절용 패널.

### Optional Components

- `PreviewListPanel`
  - 입력 목록 및 프리뷰 영역을 지원하는 패널.
- `AssetWorkspacePanel`
  - 자산/에셋 작업 영역을 제공하는 패널.
- `ComparativePreviewWidget`
  - 전/후 또는 다중 결과를 비교하기 위한 위젯.
- `CollapsibleSection`
  - 내보내기나 고급 옵션 등 접고 펼칠 수 있는 섹션 컴포넌트.
- `ElidedLabel`
  - 텍스트가 너무 길면 생략 기호(...)를 붙여 표시하는 레이블 컴포넌트.
- `DropListWidget`
  - 드롭(Drop) 입력을 지원하고 목록을 표시하는 위젯.
- `get_shell_accent_cycle()`
  - 쉘 강조색 순환 패턴 값을 가져오는 헬퍼 함수.
- `set_transparent_surface()`
  - 투명한 표면 스타일을 지정하는 헬퍼 함수.


## Template Mapping Recipes

`ui.template` 메타데이터 태그에 따른 실제 컴포넌트 매핑 레시피다.

### mini
- `HeaderSurface`
- 메인 위젯 바디
- 단일 CTA / 확인 실행 영역

### compact
- `HeaderSurface` (필요시)
- `FixedParameterPanel` (간단한 파라미터 제어)
- 단일 미리보기 영역 (`PreviewListPanel` 등)
- 실행 영역 및 그립 (`attach_size_grip`)

### full
- `HeaderSurface`
- 좌우 또는 상하 분할 레이아웃
- `PreviewListPanel` / `AssetWorkspacePanel` (에셋 및 미리보기 영역)
- `FixedParameterPanel` (파라미터 입력 영역)
- `ExportFoldoutPanel` / `CollapsibleSection` (고급 옵션/내보내기 접이식 영역)
- 하단 크기 조절 그립 (`attach_size_grip`)

### special
- `HeaderSurface`
- 특수 목적 커스텀 레이아웃
- `ComparativePreviewWidget` 등을 활용한 비교/리뷰 화면
- 필요한 Core/Common/Optional 컴포넌트만 선택적으로 조합

## Deleted / Banned Components

다음 패널 및 컴포넌트는 복잡성을 줄이고 시스템을 단순화하기 위해 **완전히 삭제되었으며 사용이 금지(Banned)**되어 있다.
앱 구현 시 이 컴포넌트들을 참조하거나 사용해서는 안 된다.

- `ExportRunPanel` (Legacy compat 레이어 삭제)
- `PresetParameterPanel` (preset과 parameter를 복합 구성하는 패널 삭제)
- `ParameterControlsPanel` (독립 파라미터 컨트롤 패널 삭제)
- `QueueManagerPanel` (대기열 관리 패널 삭제)
- `ResultInspectorPanel` (실행 결과 검사 패널 삭제)
- Hub's `VideoPreviewCard` (Hub 전용 비디오 프리뷰 카드 삭제 및 금지)
