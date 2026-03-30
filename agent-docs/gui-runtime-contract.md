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

## Shared Runtime 계약

Qt 앱들은 아래 shared API를 공통으로 믿는다.

- `ShellPalette`: 색상과 표면 배경 값
- `ShellMetrics`: 여백, 버튼 높이, 미리보기 높이, 헤더 높이
- `HeaderSurface`: 앱 상단 헤더
- `PreviewListPanel`: 입력 목록과 미리보기 영역
- `ExportRunPanel`: 레거시 실행/내보내기 패널 호환 레이어
- `ExportFoldoutPanel`: 하단 고정 액션 행을 가진 접이식 export 패널
- `panels.py`: shared panel 재수출 레이어, 구현은 `panels_export.py`, `panels_parameters.py`, `panels_preview.py`, `panels_status.py`로 분리
- `FixedParameterPanel`: 고정 파라미터 패널
- `PresetParameterPanel`: preset과 핵심 파라미터를 묶는 패널
- `ParameterControlsPanel`: 독립 파라미터 패널
- `QueueManagerPanel`: pause/retry/remove를 포함한 queue 관리 패널
- `ResultInspectorPanel`: 결과 필드/로그 검사 패널
- `ConfirmRequest`, `ConfirmChoice`, `run_confirm_dialog`: 확인 다이얼로그
- `ui.template`: manifest에서 템플릿 버킷을 명시하는 선택 필드

이름이 조금씩 다르더라도 같은 역할이면 alias로 우선 맞추고, 그 뒤에 앱 코드를 정리한다.

## Component-First 조합 규칙

앱 템플릿만으로 시작하지 말고, 가능한 경우 표준 컴포넌트 조합으로 시작한다.

기준 카탈로그는 `agent-docs/qt-component-catalog.md`를 따른다.

핵심 컴포넌트 축:

- `HeaderSurface`
- `attach_size_grip()`
- `InputCard`
- `PreviewCard`
- `StatusCard`
- `QueueCard`
- `ExecutionCard`
- `FullSplitWorkspace`

현재 shared runtime이 직접 제공하지 않는 항목도 먼저 “표준 역할”로 정의하고, 반복 사용이 확인되면 shared panel/helper로 승격한다.

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
- `ui.template`: `full`, `compact`, `mini`, `special` 중 하나를 명시할 때 사용

`ui.template`는 특히 `special` 앱을 코드가 아닌 manifest에서 식별하기 위해 사용한다.
다른 템플릿은 점진적으로 채워도 되지만, 특수 GUI는 먼저 명시하는 쪽이 안전하다.

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
