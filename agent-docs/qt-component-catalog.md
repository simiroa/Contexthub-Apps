# Qt Component Catalog

이 문서는 `Contexthub-Apps`의 Qt 앱을 앱 단위 템플릿만이 아니라 컴포넌트 조합 단위로 정리하기 위한 기준 카탈로그다.

## Why

현재 shared runtime에는 공통 shell과 일부 panel이 있지만, 새 앱 작성 시 여전히 앱 단위 복제 의존이 크다.
이를 줄이기 위해 앱은 아래 두 층으로 본다.

1. 템플릿 버킷
   - `mini`
   - `compact`
   - `full`
   - `special`
2. 표준 컴포넌트
   - 헤더
   - 입력 카드
   - 프리뷰 카드
   - 상태 카드
   - 큐 카드
   - 실행 카드
   - split workspace
   - 도메인 프리뷰
   - 입력/배치 제어
   - 특수 작업 카드

## Standard Components

### Header

- `HeaderSurface`
- 앱 이름 + 아이콘 버튼만 사용
- 부제목, open 버튼, 상태 배지는 기본값에서 숨김

### Grip

- `attach_size_grip()`
- `mini` 제외 공통 규칙

### InputCard

짧은 source input, URL 입력, 파일 선택, drop target의 시작점.

### PreviewCard

현재 대상 미리보기나 분석 결과를 보여주는 카드.

### StatusCard

짧은 안내, 현재 상태, dependency 상태 요약용 카드.

### QueueCard

queue가 실제 제품 개념일 때만 사용.
compact에서는 높이를 제한한다.

### QueueManagerCard

queue 자체가 제품 기능이고 pause/retry/remove 같은 관리 동작이 필요할 때 쓰는 카드.

### ExecutionCard

출력 경로, 진행률, 상태, 메인 CTA를 담는 실행 영역.

### FullSplitWorkspace

`full` 또는 일부 `special`에서 쓰는 좌우 분할 작업 영역.

## Domain Preview Components

### ImagePreviewCard

단일 이미지 미리보기와 짧은 메타데이터.

### AudioPreviewCard

waveform, 재생/정지, 길이 같은 오디오 미리보기.

### VideoPreviewCard

썸네일, 길이, 해상도, fps 중심의 비디오 미리보기.

### DocumentPreviewCard

페이지 썸네일, 페이지 수, OCR 상태를 보여주는 문서 미리보기.

### Viewport3DCard

3D 모델 프리뷰 shell과 뷰 상태 표시.

## Input / Batch Components

### DropZoneCard

drag and drop 중심 입력 카드.

### BatchListCard

배치 입력 리스트, 파일 리스트, 작업 리스트.

### PromptCard

긴 텍스트 입력용 카드.

### HistoryPanel

recent files, session history, project history용 패널.

### PresetSelectorCard

preset 선택과 설명을 함께 보여주는 카드.

full에서는 파라미터 카드보다 위에 두는 것을 기본값으로 본다.

### PresetParameterCard

preset과 핵심 파라미터를 한 카드에 묶는 기본 full 컴포넌트. 카드 구분을 최소화할 때 우선 사용한다.

### ParameterControlsCard

full에서 preset이 없거나, 추가 파라미터 카드가 정말 더 필요할 때 쓰는 독립 파라미터 블록.

### ModelSelectorCard

모델 선택과 모델 상태를 보여주는 카드.

### ParameterStrip

slider 중심의 짧은 파라미터 묶음.

## Execution / State Components

### CollapsibleSection

내보내기나 고급 옵션처럼 항상 펼쳐둘 필요가 없는 섹션을 접이식으로 다루는 표준 컴포넌트.

### ExportFoldoutCard

`full` 템플릿의 기본 export UI. 접힌 상태에서도 액션 행이 보이고, 펼치면 출력 옵션과 실행 세부가 드러나는 카드.

### OutputOptionsCard

출력 포맷, 파일명 규칙, 후속 액션 묶음.

### ProgressStatusBar

상태 텍스트 + 진행률 + 메인 CTA 조합.

### DependencyStatusCard

ffmpeg, blender, model service 같은 의존성 상태 카드.

### EmptyStateCard

빈 상태 안내를 공통 방식으로 처리하는 카드.

### ResultInspectorCard

실행 결과의 메타데이터, 로그, 필드별 상세를 확인하는 카드.

## Special Task Components

### ToolbarRow

view mode, filter, action 모음 행.

### CompareWorkspace

before/after, left/right, diff용 작업 영역.

### ChannelMapCard

채널 매핑/패킹용 카드.

## Review Focus

새 스킬이나 기존 앱 정리 시 아래 항목은 누락되기 쉬우므로 별도 확인 대상으로 본다.

- `QueueManagerCard`
- `ResultInspectorCard`
- `AudioPreviewCard`
- `VideoPreviewCard`
- `DocumentPreviewCard`
- `Viewport3DCard`
- `ChannelMapCard`

## Template Mapping

### mini

- `HeaderSurface`
- main body card
- status/execution block

### compact

- `InputCard`
- `PreviewCard` 또는 `StatusCard`
- integrated `ExecutionCard`
- optional `QueueCard`

### full

- `HeaderSurface`
- `FullSplitWorkspace`
- preview 위, input list 아래
- preset이 있으면 preset+parameter를 한 카드로 먼저 둠
- parameter 우선, export는 접이식 section
- export는 우측 컬럼의 최하단

### special

- `HeaderSurface`
- custom workspace
- 필요한 표준 컴포넌트만 선택적으로 삽입

## Current Shared Runtime Coverage

현재 shared runtime이 직접 제공하는 대표 클래스는 다음이다.

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

이 문서의 나머지 컴포넌트는 개념 카탈로그로 먼저 정의하고, 필요 시 shared runtime helper나 panel로 점진적으로 승격한다.
