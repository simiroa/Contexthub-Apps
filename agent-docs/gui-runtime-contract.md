# GUI Runtime Contract

## 목적

이 문서는 `Contexthub-Apps`에서 Qt 기반 앱을 정리할 때 기준이 되는 공통 계약을 정리한다.
핵심 목적은 다음과 같다.

- 앱별 UI 모양 차이는 허용하되, 공통 컴포넌트 이름과 속성은 안정적으로 유지한다.
- 번역, 테마, 컬러, 여백, 공통 헤더/패널 규칙을 shared runtime 쪽으로 모은다.
- 리팩토링 순서를 낮은 리스크부터 잡는다.

## 템플릿 분류

Qt 앱은 아래 4개 템플릿으로 본다.

### 1. Full GUI

미리보기와 배치/리스트를 함께 다루고, preset/parameter가 여러 개 있으며, 접이식 내보내기나 실행 옵션까지 가지는 작업 화면형 앱이다.

예시 성격:

- 이미지 변환/비교/벡터화
- 문서 변환/스캔/병합
- 비디오 변환류
- 일부 ComfyUI 전용 고밀도 UI

### 2. Compact GUI

다중 input list가 없고, `preview`나 `list` 중 하나만 있으며, 파라미터가 많지 않아 한 화면에서 바로 확인 가능한 1단 실행형 앱이다.

예시 성격:

- 단일 source 입력 + 짧은 상태/실행 화면
- 단순 옵션 몇 개와 바로 실행되는 툴
- input, status, execute가 수직으로 정리되는 앱

### 3. Mini GUI

옵션이 많지 않고, 다중 input을 지원하더라도 리스트가 아니라 총량/선택 요약/확인 중심인 작은 confirm shell에 가까운 창이다.

예시 성격:

- 확인 후 콘솔/백엔드 흐름으로 넘기는 confirm shell
- 현재 선택 요약과 단일 CTA만 필요한 작은 유틸리티
- 입력 리스트보다 "선택된 항목 몇 개를 실행할지" 확인이 중요한 앱

### 4. Special GUI

일반 공통 템플릿으로 묶기 어려운 앱이다.
비교/리뷰/워크스페이스/대시보드처럼 상호작용 규칙이 강하다.

## Shared Runtime 계약 (API surface)

Qt 앱들은 K14 디자인 문서에 나열된 아래 shared API를 공통으로 믿고 사용한다.

### Core Components
- `build_shell_stylesheet`, `HeaderSurface`, `apply_app_icon`, `attach_size_grip`, `get_shell_metrics`, `get_shell_palette`, `refresh_runtime_preferences`, `runtime_settings_signature`, `run_confirm_dialog`, `set_surface_role`, `set_button_role`, `set_badge_role`, `qt_t`
- `BaseAppWindow`: 공통 Qt GUI 윈도우 베이스 클래스 (창 상태 복원, 핫 리로드 타이머 등 제공)

### Common Components
- `ExportFoldoutPanel`, `FixedParameterPanel`

### Optional Components
- `PreviewListPanel`
- `AssetWorkspacePanel`
- `ComparativePreviewWidget`
- `CollapsibleSection`
- `ElidedLabel`
- `DropListWidget`
- `get_shell_accent_cycle`
- `set_transparent_surface`

## Deleted / Banned Components

다음 컴포넌트 및 패널은 디자인 단순화를 위해 삭제/금지되었으며, 어떠한 앱에서도 사용하거나 참조할 수 없다. (D1 / Zero-caller 패널)

- `ExportRunPanel`
- `PresetParameterPanel`
- `ParameterControlsPanel`
- `QueueManagerPanel`
- `ResultInspectorPanel`
- Hub's `VideoPreviewCard` (Hub-only)

## Template Enum Policy (`ui.template` = Tag Only)

- **`ui.template` is an inventory/capture tag only.**
- 앱 `manifest.json`의 `ui.template` 필드(full/compact/mini/special)는 순수하게 메타데이터 관리, 앱 인벤토리 분류, 그리고 GUI 캡처 스윕(capture-sweep) 스크립트에서 참조하기 위한 태그일 뿐이다.
- 런타임 프레임워크가 이 태그 값을 읽어 특정 클래스를 로드하거나 윈도우 구조를 동적으로 주입하는 등의 런타임 클래스 로더 역할을 수행해서는 안 된다.
## K2: Base Class Standardization Rule (공용 윈도우 베이스 클래스 표준화)

- **Standardize on `BaseAppWindow` for Qt GUI application windows to consolidate settings persistence, frameless window flags, custom icon handling, and runtime preferences reload timing.**
- 공통 `BaseAppWindow`를 표준으로 도입하여 창 상태/위치 복원(`QSettings`), 프레임리스 윈도우 플래그, 마우스 드롭 이벤트 처리, 테마/설정 핫 리로드 타이머 등 공통 보일러플레이트 로직을 통합 관리한다.
- 개별 앱에서의 불필요한 보일러플레이트 중복 코드를 제거하고 강한 결합을 방지하기 위해 공용 런타임 내 표준 `BaseAppWindow`를 상속하여 구현하는 것을 권장한다. (이미 17개 앱이 `BaseAppWindow`를 상속받는 구조로 리팩토링 및 통합이 완료됨)

## Two-Plane SSOT Concept (단일 진실 공급원)

공유 런타임(Shared Runtime) 소스 코드의 동기화 및 릴리즈 구조는 다음 **Two-Plane SSOT** 개념을 철저히 따른다.

1. **Product Shared runtime original** = `Hub Runtimes/Shared`
   - 실제 서비스 환경에서 구동되는 프로덕션 런타임 소스의 원본(Original)이다.
2. **Dev Shared mirror original** = Apps `dev-tools/runtime/Shared`
   - 앱 개발 환경 및 패키징 시 검증에 사용되는 개발용 미러 원본(Mirror Original)이다.
3. **Market ZIP never contains Shared runtime code.**
   - 배포 마켓에 업로드되는 각 개별 앱의 ZIP 파일은 어떠한 경우에도 Shared runtime 코드를 내장하거나 포함해서는 안 된다. Shared runtime은 플랫폼 서비스(Hub)에서 공통으로 로드하고 제공한다.
4. **Release Gate (K13) requirement:**
   - 임의로 `dev-tools/runtime/Shared` 코드를 수정하여 배포해서는 안 된다.
   - Shared runtime의 동작이나 코드를 변경할 때는 반드시 **연관된 Hub의 커밋/PR을 명시하거나 동기화(sync) 계획**을 함께 릴리즈 게이트 문서에 기재해야 한다.

## Theme Contract

Qt GUI의 테마 계약은 이제 선택 사항이 아니라 고정 규칙으로 본다.

- `ui.shared_theme`는 Qt 앱에서 `contexthub`만 사용한다.
- 앱별 컴포넌트 구조 차이는 허용하지만, 색상/톤/표면/강조 규칙은 shared runtime이 담당한다.
- `special` 앱도 레이아웃과 상호작용만 특수할 뿐, 색 체계는 공통 계약을 따른다.

### 금지 규칙

유지보수 비용을 줄이기 위해 아래 패턴은 신규/정리 코드에서 금지한다.

- 앱 코드에서 raw hex 색 (`#RRGGBB`, `#RRGGBBAA`)을 직접 넣는 `setStyleSheet()`
- 앱 코드에서 `rgb(...)`, `rgba(...)`를 직접 조합하는 로컬 stylesheet
- 같은 역할의 버튼/배지/패널을 앱마다 다른 색 조합으로 재정의하는 것

### 권장 방식

- 버튼, 배지, 패널, 상태 강조는 shared shell의 role/tone helper 또는 동등한 property API로 지정한다.
- 앱 코드는 레이아웃과 상태만 결정하고, 시각 토큰 조합은 shared runtime으로 올린다.
- 예외가 필요하면 shared runtime에 role을 추가한 뒤 앱에서 그 role을 사용한다.

### 현재 안정화한 호환 항목

- `HeaderSurface.manual_btn` alias 유지
- `PreviewListPanel.set_comparative_mode()` 호환 유지
- `ShellPalette.surface_subtle` / `field_bg` / `border` 유지
- `ShellMetrics.preview_min_height` / `primary_button_height` / `header_*` 유지
- `confirm_dialog.py` 복구

## Manifest 지정

권장 규칙:

- `ui.framework`: 실제 렌더링 엔진
- `ui.shared_theme`: 공통 테마 계약
- `ui.template`: `full`, `compact`, `mini`, `special` 중 하나를 명시할 때 사용 (순수 메타데이터/태그 용도)

## 문서화 기준

이 저장소에서 문서화는 두 층으로 나눈다.

### 설계/규칙

`agent-docs/`에 둔다.

- 공통 계약
- 템플릿 분류
- 작업 우선순위
- 리스크 기준

### 실행 결과/진단

`Diagnostics/`에 둔다.

- GUI 캡처 로그
- 실패한 앱과 traceback
- 특정 날짜의 정리 결과

## 리스크 우선순위

리팩토링은 아래 순서로 진행한다.

1. shared runtime alias 복구
2. confirm dialog 같은 공통 모듈 복구
3. 템플릿 분류 정리
4. low-risk 앱부터 캡처 재검증
5. 남은 특수 앱은 별도 축으로 관리

## 현재 판단

현재 상태에서는 다음 해석이 가장 안전하다.

- `full gui`: 이미지/문서/비디오의 고밀도 Qt 앱
- `compact gui`: 다중 입력 리스트 없이 바로 확인 가능한 1단 실행형 GUI
- `mini gui`: 총량/선택 요약/확인 중심의 작은 confirm shell
- `special gui`: ComfyUI/비교/리뷰형 앱

이 분류는 UI 스타일이 아니라, 유지보수 방식과 shared runtime 계약의 강도에 맞춘 분류다.

## Enforcement

공통 계약은 문서만으로 끝내지 않는다.

1. shared runtime은 role/tone 기반 스타일 API를 제공한다.
2. manifest 검사는 Qt 앱의 `ui.shared_theme = contexthub`를 확인한다.
3. 검사 스크립트는 앱 코드의 raw color stylesheet를 경고 또는 실패 대상으로 수집한다.
4. 승인된 legacy 예외는 별도 `EXEMPT`로 분리하고, 실제 drift와 혼동하지 않는다.
