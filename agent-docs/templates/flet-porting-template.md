# Flet Porting Template

이 문서는 기존 Python GUI 앱을 `Flet`으로 옮길 때, 다른 에이전트가 그대로 따라 시작할 수 있는 최소 템플릿이다.

목적:

- 반복되는 wrapper 실수 방지
- `service / state / flet_app` 분리 강제
- 공통 토큰/창/다이얼로그 사용 유도
- 미완성 포팅을 “완료된 것처럼” 남기는 실수 방지

## 1. 권장 파일 구조

```text
{category}/{app_id}/main.py
{category}/{app_id}/manifest.json
{category}/{app_id}/manual.md

{category}/_engine/features/.../{app_name}/
  service.py
  state.py
  flet_app.py
```

## 2. main.py 템플릿 원칙

`main.py`는 아래 역할만 가진다.

- `APP_ROOT`, `LEGACY_ROOT` 계산
- `CTX_APP_ROOT` 설정
- `_engine` 경로 주입
- target 수집
- `features....flet_app.start_app(...)` 호출

금지:

- `main.py` 안에서 Flet UI 직접 구성
- `logger`를 선언하지 않고 예외 처리에서 사용
- Flet import 실패를 다른 예외로 덮어쓰기

권장 패턴:

```python
def _run_flet(targets):
    from features.somewhere.some_app.flet_app import start_app
    start_app(targets)
```

## 3. flet_app.py 템플릿 원칙

반드시 아래 흐름을 따른다.

1. 공통 토큰 import
2. 공통 page configure
3. 상태 객체 생성
4. 컨트롤 생성
5. UI 조립
6. 이벤트 핸들러 연결

기본 import:

```python
from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.window import apply_desktop_window
```

금지:

- 색상/간격/창 크기 하드코딩
- 서비스 호출을 이벤트 핸들러 안에서 즉흥적으로 직접 조합
- 아직 없는 핸들러 이름을 UI에 먼저 연결
- `pass` 상태인 버튼/파일 피커를 완료된 앱처럼 남기기

## 4. service.py 템플릿 원칙

`service.py`는 다음만 책임진다.

- 파일 처리
- 모델/외부 프로세스 호출
- 포맷 변환
- 검증 로직

금지:

- Flet import
- UI 상태 직접 변경
- page/dialog/snackbar 직접 호출

권장 추가:

- 의존성 프리체크 함수(`get_missing_dependencies`)를 제공
- 필수/선택 의존성을 구분해서 반환

## 5. state.py 템플릿 원칙

`state.py`는 아래를 분리한다.

- 입력 데이터
- 선택 상태
- 작업 상태
- 출력 상태

최소 예시:

```python
@dataclass
class SomeAppState:
    files: list = field(default_factory=list)
    is_processing: bool = False
    status_text: str = "Ready"
```

## 6. 공통 실패 패턴

반드시 먼저 체크할 것:

1. `main.py`에서 import한 `start_app()`가 실제 존재하는가
2. `main.py` 예외 처리에서 선언되지 않은 `logger`를 쓰고 있지 않은가
3. `flet_app.py`가 `COLORS["bg"]`, `COLORS["background"]`, `COLORS["text_dim"]` 같이 현재 토큰에 없는 키를 참조하지 않는가
4. UI에서 연결한 `on_pick_files`, `on_clear_all`, `btn_extract` 같은 이름이 실제로 존재하는가
5. `service.py`가 relative import를 쓰는데 `main.py`는 top-level import처럼 실행하고 있지 않은가
6. `pass`로 남은 버튼/파일 피커/핸들러가 없는가

## 6.1 Flet 0.82 호환 체크리스트

현재 런타임(`flet==0.82.x`) 기준으로 아래를 반드시 지킨다.

- `ElevatedButton(text="...")` 사용 금지  
  `ElevatedButton("...")` 또는 `content=ft.Text("...")` 사용
- `Dropdown(on_change=...)` 사용 금지  
  `Dropdown(on_select=...)` 사용
- `ComboBox` 사용 금지  
  `Dropdown`으로 통일
- `FilePicker(on_result=...)` 가정 금지  
  `picker = ft.FilePicker()` 후 `files = picker.pick_files(...)` 반환값 직접 처리
- `ft.Center(...)` 사용 금지  
  `ft.Row(..., alignment="center")` 또는 `ft.Container(..., alignment=...)` 사용
- `ft.alignment.center` 사용 금지  
  `ft.alignment.Alignment(0, 0)` 사용
- `ft.icons.*` 상수 의존 금지  
  아이콘 문자열(`"add"`, `"delete_outline"`, `"arrow_forward"`) 사용

포팅 시작 전 `inspect.signature()`로 실제 API를 확인한다.

```python
import inspect
import flet as ft

print(ft.__version__)
print(inspect.signature(ft.ElevatedButton))
print(inspect.signature(ft.Dropdown))
print(inspect.signature(ft.FilePicker))
```

## 7. 완료 기준

아래를 만족해야 “포팅 완료”로 본다.

- GUI 부팅 성공
- 대표 기능 1개 성공
- 실패 경로 1개 확인
- `manual.md` 갱신
- 공통 토큰 사용
- 미구현 버튼 없음
- 의존성 누락 시 즉시 안내(작업 시작 전) 동작 확인
- 최소 기능 스모크 리포트 1개 생성

예시(이미지 카테고리):

- `Diagnostics/image_feature_smoke.py`
- `Diagnostics/generated/image_feature_smoke/smoke_report.json`

## 8. 임시 포팅 상태 표기

아직 미완성이면 문서와 코드 주석에 명시한다.

예:

- `Flet migration preview`
- `File picker not wired yet`
- `Slider mode not implemented yet`

하지만 매뉴얼/manifest에 정식 앱처럼 적지 않는다.
