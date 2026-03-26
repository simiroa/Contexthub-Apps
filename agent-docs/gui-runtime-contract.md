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

좌우 또는 상하 분할 구조가 있고, 미리보기와 파라미터, 실행/결과가 분리된 앱이다.

예시 성격:

- 이미지 변환/비교/벡터화
- 문서 변환/스캔/병합
- 비디오 변환류
- 일부 ComfyUI 전용 고밀도 UI

### 2. Compact GUI

입력 선택과 실행 버튼, 진행 상태가 중심인 단순한 화면이다.

예시 성격:

- 파일 선택 후 확인만 거치는 앱
- 실제 작업은 콘솔이나 백엔드가 담당하고, GUI는 확인/진행창 역할만 하는 앱

### 3. Mini GUI

단일 작업 중심의 가벼운 입력창이다.
세부 패널이 적고, 독립 다이얼로그에 가깝다.

### 4. Special GUI

일반 공통 템플릿으로 묶기 어려운 앱이다.
비교/리뷰/워크스페이스/대시보드처럼 상호작용 규칙이 강하다.

## Shared Runtime 계약

Qt 앱들은 아래 shared API를 공통으로 믿는다.

- `ShellPalette`: 색상과 표면 배경 값
- `ShellMetrics`: 여백, 버튼 높이, 미리보기 높이, 헤더 높이
- `HeaderSurface`: 앱 상단 헤더
- `PreviewListPanel`: 입력 목록과 미리보기 영역
- `ExportRunPanel`: 실행/내보내기 패널
- `FixedParameterPanel`: 고정 파라미터 패널
- `ConfirmRequest`, `ConfirmChoice`, `run_confirm_dialog`: 확인 다이얼로그
- `ui.template`: manifest에서 템플릿 버킷을 명시하는 선택 필드

이름이 조금씩 다르더라도 같은 역할이면 alias로 우선 맞추고, 그 뒤에 앱 코드를 정리한다.

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
- `compact gui`: confirm+console 하이브리드 앱
- `mini gui`: 작은 단일 작업용 GUI
- `special gui`: ComfyUI/비교/리뷰형 앱

이 분류는 UI 스타일이 아니라, 유지보수 방식과 shared runtime 계약의 강도에 맞춘 분류다.
