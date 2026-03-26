# GUI Issues Found (2026-03-13)

## 범위

캡처 결과 기준으로 `ai` 카테고리 일부와 `rigreader_vectorizer`의 GUI 문제를 분류했다.

관련 캡처:

- `Diagnostics/gui_captures/ai/marigold_pbr.png`
- `Diagnostics/gui_captures/image/rigreader_vectorizer.png`

## Findings

### 1. `ai` 툴은 좁은 헤더에 모델 관리자 프레임을 붙여 버튼/상태가 잘림

대표 증상:

- `marigold_pbr` 캡처에서 상단 모델 카드 텍스트와 상태가 잘림
- 다운로드 버튼은 보이지만 모델명/상태 라벨이 카드 폭보다 길어 일부만 노출됨

원인:

- [ai/_engine/features/ai/marigold_gui.py#L51](C:/Users/HG/Documents/Contexthub-Apps/ai/_engine/features/ai/marigold_gui.py#L51) 에서 창 폭이 `420`으로 좁음
- [ai/_engine/features/ai/marigold_gui.py#L138](C:/Users/HG/Documents/Contexthub-Apps/ai/_engine/features/ai/marigold_gui.py#L138) 부근 헤더는 `pack(side="left")` 제목 + `pack(side="right")` 모델 카드 구조
- 공용 [gui_lib.py#L583](C:/Users/HG/Documents/Contexthub-Apps/dev-tools/runtime/Shared/contexthub/utils/gui_lib.py#L583) 의 `ModelManagerFrame`은 내부 텍스트와 버튼 폭이 고정에 가깝고 좁은 부모 폭을 고려한 축약/줄바꿈 처리가 없음

의미:

- `marigold_pbr` 하나의 문제가 아니라 `ModelManagerFrame`을 쓰는 `subtitle.py`, `upscale_app.py` 계열에도 재현될 가능성이 높음

수정 방향:

- 헤더를 `grid` 기반 2행 구조로 바꿔 제목과 모델 카드 분리
- `ModelManagerFrame`에 최소 폭, 텍스트 줄바꿈, compact 모드 또는 축약형 상태 UI 추가
- 캡처 테스트를 `ai` 카테고리 공통 회귀 항목으로 유지

### 2. `rigreader_vectorizer`는 전형적인 i18n 키 누출 상태

증상:

- 대부분의 라벨과 버튼이 `rigready_vectorizer_gui.*` 키 문자열 그대로 표시됨
- 실제 창 구조는 비교적 안정적이지만 텍스트 품질이 거의 깨진 상태

원인:

- [image/_engine/features/image/vectorizer/vectorizer_gui.py#L92](C:/Users/HG/Documents/Contexthub-Apps/image/_engine/features/image/vectorizer/vectorizer_gui.py#L92) 이하에서 `t("rigready_vectorizer_gui...")`를 광범위하게 사용
- 현재 [image/_engine/locales.json](C:/Users/HG/Documents/Contexthub-Apps/image/_engine/locales.json) 에는 `rigready_vectorizer_gui.*` 키가 정의되어 있지 않음
- 앱 전용 locale 로딩 또는 카테고리 locale 키 정합성이 맞지 않는 상태

수정 방향:

- `rigready_vectorizer` 관련 locale 키를 카테고리 `image/_engine/locales.json` 또는 앱 전용 locale 중 한 곳으로 일관되게 정의
- 앱 전용 locale를 둘 경우 `main.py`에서 명시 로딩
- 핵심 버튼/헤더에는 fallback 문자열 추가

## 공통 문제 유형으로 묶이는 항목

- i18n 리소스 누락 또는 로딩 누락
- 공통 `BaseWindow` 패턴 미사용
- 좁은 폭 + 가로 배치 과밀
- 하드코딩 문자열 혼용

## 다음 수정 우선순위

1. `rigreader_vectorizer` locale 키 정합성 복구
2. `ModelManagerFrame` 또는 `ai` 헤더 레이아웃 개선
3. 전 카테고리 GUI 캡처 재실행

## 재사용 문서

반복 분석을 줄이기 위한 공통 절차는 [gui-issue-playbook.md](C:/Users/HG/Documents/Contexthub-Apps/agent-docs/gui-issue-playbook.md)에 정리했다.

## Resolved In This Session

### 1. `ai` 카테고리 모델 관리자/푸터 잘림

조치:

- 공용 [gui_lib.py](C:/Users/HG/Documents/Contexthub-Apps/dev-tools/runtime/Shared/contexthub/utils/gui_lib.py) 의 `ModelManagerFrame`에 줄바꿈과 리사이즈 대응을 추가
- [marigold_gui.py](C:/Users/HG/Documents/Contexthub-Apps/ai/_engine/features/ai/marigold_gui.py) 에서 헤더를 2행 구조로 정리
- `esrgan_upscale`, `whisper_subtitle`, `rmbg_background`는 `footer_frame` 기준으로 액션 버튼/진행 바를 고정

결과:

- 모델 카드 텍스트와 다운로드 버튼이 잘리지 않음
- AI 툴의 실행/취소 버튼이 첫 화면에 노출됨
- 캡처 결과에서 `esrgan_upscale`, `whisper_subtitle`, `rmbg_background`의 하단 액션이 확인됨

### 2. `rigreader_vectorizer`

조치:

- 앱 전용 [locales.json](C:/Users/HG/Documents/Contexthub-Apps/image/rigreader_vectorizer/locales.json) 추가
- 래퍼가 앱 로케일을 읽도록 `APP_ROOT` 수정
- 창 최소 폭과 주요 행 레이아웃을 넓혀 버튼 잘림을 방지

결과:

- `rigready_vectorizer_gui.*` 키 문자열 노출이 사라짐
- 출력 폴더 행과 실행 버튼이 안정적으로 보임

### 4. `doc_scan`

조치:

- [scan_gui.py](C:/Users/HG/Documents/Contexthub-Apps/document/_engine/features/document/scan_gui.py) 를 `ctk.CTk`에서 `BaseWindow` 기반으로 전환
- 공통 테마 상수로 버튼 색상과 카드 경계를 맞춤
- 캔버스 리사이즈 바인딩을 본문 캔버스로 정리

결과:

- 문서 카테고리에서도 공통 타이틀 바/테마/언어 체인이 유지됨
- 구형 독립 테마 설정 호출이 제거됨
