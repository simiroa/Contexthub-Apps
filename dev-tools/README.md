# Local App Test Tools

이 폴더는 `Contexthub-Apps` 안에서 개별 앱을 직접 실행하고 GUI를 캡처하기 위한 로컬 테스트 도구 모음이다.

## 전제 조건

- Python 3.11 사용 가능
- `dev-tools\runtime\Shared` 존재 또는 원본 허브 저장소 존재
- 필요한 패키지가 현재 Python 환경에 설치되어 있어야 함
- `ai` 카테고리 기능 테스트 시 Conda 권장
  - 기본 권장 env 이름은 `contexthub-ai`
  - Conda가 없으면 실제 허브 런타임은 경고 후 일반 Python으로 fallback 하도록 정리되어 있음

## 포함 스크립트

- `sync-shared-runtime.ps1`: `dev-tools\runtime\Shared`를 허브 저장소 `Runtimes\Shared`로 미러링
- `run-app-local.ps1`: 카테고리/앱을 지정해 일반 실행
- `run-image-resize-local.ps1`: `image/resize_power_of_2` 전용 빠른 실행 예시
- `capture-python-gui-apps.ps1`: Python GUI 앱들을 순회하며 창 캡처와 로그 생성

## 예시

실제 파일로 실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\dev-tools\run-app-local.ps1 `
  -Category image `
  -App resize_power_of_2 `
  -TargetPath "C:\path\to\image.png"
```

헤드리스 샘플 입력으로 실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\dev-tools\run-app-local.ps1 `
  -Category image `
  -App resize_power_of_2 `
  -Headless
```

빠른 실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\dev-tools\run-image-resize-local.ps1 `
  -TargetPath "C:\path\to\image.png"
```

## 주의

- 허브에서 실제 앱 실행을 테스트하기 전에는 `sync-shared-runtime.ps1`로 shared runtime을 먼저 허브 쪽에 반영하는 것이 기준이다.
- 기본 우선순위는 `dev-tools\runtime\Shared`다. 없으면 허브 저장소의 `Runtimes\Shared`를 사용한다.
- 일부 앱은 공유 런타임 외에 모델, 외부 바이너리, 설치형 도구가 추가로 필요하다.
- GUI 앱은 실행 후 창이 열린 상태로 대기하는 것이 정상이다.
- `ai` 카테고리의 실제 추론은 GUI만 뜨는 것과 별개로 Conda env, 모델, GPU/외부 바이너리 상태에 따라 달라진다.
- `ai/qwen3_tts`는 이제 Flet 전용 앱이므로, 실행 Python 또는 `contexthub-ai` env에 `flet`이 실제 설치되어 있어야 한다.
- GUI 회귀는 `capture-python-gui-apps.ps1` 기준 스크린샷과 `Diagnostics/gui_capture_log.md`를 함께 본다.
