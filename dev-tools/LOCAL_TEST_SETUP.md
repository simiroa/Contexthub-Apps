# Local Test Setup

## 목적

Contexthub 앱 설치 환경 없이도, 이 저장소의 앱을 개별적으로 실행해 보는 최소 로컬 테스트 경로를 제공한다.

## 핵심 아이디어

이 저장소만으로는 일부 앱이 바로 실행되지 않는다. 이유는 다음과 같다.

- 카테고리 `_engine/utils`가 허브 공유 런타임 모듈을 전제로 동작함
- `utils.explorer`, `utils.files`, `utils.i18n`, `utils.batch_runner` 같은 모듈이 `Runtimes\Shared\contexthub\utils`에 있음
- i18n 설정 파일도 `Runtimes\Shared\config\i18n` 아래에 있음

따라서 로컬 테스트 시 아래 환경 변수가 중요하다.

- `PYTHONPATH=<SharedRoot>`
- `CTX_SHARED_ROOT=<SharedRoot>\contexthub`

여기서 `<SharedRoot>`는 다음 우선순위를 가진다.

1. `Contexthub-Apps\dev-tools\runtime\Shared`
2. `C:\Users\HG\Documents\Contexthub\Runtimes\Shared`

## 현재 확인된 상태

`image/resize_power_of_2`는 위 환경을 주고 실제 PNG 파일 경로를 넘기면 GUI가 정상적으로 올라온다.

추가로 현재 기준:

- `prompt_master`, `rigreader_vectorizer`, `doc_scan`은 GUI 규격 수정 후 캡처 검증됨
- `esrgan_upscale`, `rmbg_background`, `whisper_subtitle`는 하단 액션 버튼 노출까지 재검증됨
- `ai` 카테고리 런타임은 Conda 우선 규칙을 가지지만, 로컬 캡처 테스트는 기존 Python fallback 환경에서도 가능하다
- `ai/qwen3_tts`는 legacy GUI fallback 없이 Flet 전용으로 전환되었고, 테스트 Python 또는 `contexthub-ai` env에 `flet` 설치가 전제된다

## 로컬 복제 권장 이유

앱 코드의 경로 로직을 바꾸면 이식성과 실제 설치 환경 검증이 흐려진다. 그래서 앱 코드 자체는 그대로 두고, 테스트 런처만 로컬 공유 런타임 경로를 주입하는 방식이 안전하다.

이 방식의 장점:

- 앱 코드가 실제 배포 경로 가정에서 벗어나지 않음
- 테스트용 공유 파일을 저장소 내부에서 관리 가능
- 나중에 허브 밖으로 앱을 이식할 때도 테스트 레이어만 교체하면 됨

## 추천 절차

1. 허브 저장소가 로컬에 존재하는지 확인
2. `dev-tools/sync-shared-runtime.ps1`로 공유 런타임 복제
3. 필요한 Python 패키지 설치 확인
4. `ai` 카테고리라면 Conda env 사용 여부를 먼저 확인
5. `dev-tools/run-app-local.ps1`로 대상 앱 실행
6. GUI 앱은 실제 파일을 넘겨서 테스트
7. 파일 선택이 귀찮으면 `-Headless`로 샘플 입력 경로를 공급
8. GUI 수정 후에는 `dev-tools/capture-python-gui-apps.ps1`로 회귀 캡처

## 예시

```powershell
powershell -ExecutionPolicy Bypass -File .\dev-tools\run-app-local.ps1 `
  -Category image `
  -App resize_power_of_2 `
  -TargetPath "$env:TEMP\sample.png"
```

```powershell
powershell -ExecutionPolicy Bypass -File .\dev-tools\run-image-resize-local.ps1 `
  -Headless
```

```powershell
powershell -ExecutionPolicy Bypass -File .\dev-tools\sync-shared-runtime.ps1
```

## AI 카테고리 메모

실제 허브 공유 런타임은 다음 설정 키를 참조해 AI 실행 환경을 해석한다.

- `AI_ENV_MODE`
- `AI_CONDA_EXE`
- `AI_CONDA_ENV_NAME`
- `AI_CONDA_ENV_PATH`

기본값은 `AI_ENV_MODE=prefer_conda`, `AI_CONDA_ENV_NAME=contexthub-ai`다.
Conda가 없거나 env를 찾지 못하면 경고 후 기존 Python으로 fallback 한다.

### Qwen3-TTS Flet 메모

- 현재 확인된 `flet` 설치 경로
  - `C:\Users\HG\Documents\HG_context_v2\ContextUp\tools\python\python.exe`
  - `C:\Users\HG\miniconda3\envs\contexthub-ai\python.exe`
- 버전: `flet 0.82.2`

## 관련 기록

- GUI 이슈 유형: `agent-docs/gui-issue-playbook.md`
- 이번 GUI 수정 요약: `Diagnostics/gui-issues-2026-03-13.md`
- 최신 캡처 기준: `Diagnostics/gui-capture-report-2026-03-13.md`
