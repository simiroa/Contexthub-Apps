# GUI Capture Tool Guide

이 문서는 `dev-tools/capture-python-gui-apps.ps1` 스크립트를 사용하여 Contexthub 미니앱의 GUI를 자동으로 캡처하는 도구에 대해 설명합니다.

## 1. 개요
GUI Capture Tool은 저장소 내의 모든 Python GUI 앱을 자동으로 실행하고, 창이 뜨면 스크린샷을 찍어 `Diagnostics/gui_captures` 폴더에 저장하는 회귀 테스트용 도구입니다.

## 2. 작동 메커니즘
도구는 다음과 같은 순서로 작동합니다:

1.  **앱 검색**: 지정된 카테고리 폴더에서 `manifest.json`을 찾아 `ui.enabled`가 `true`이고 `entry_point`가 `.py`인 앱을 식별합니다.
2.  **환경 설정**: 앱 실행 전 다음 환경 변수를 설정합니다.
    - `CTX_CAPTURE_MODE=1`: 앱이 캡처 모드로 동작하도록 지시합니다. (UI 배치 최적화 등)
    - `CTX_HEADLESS=1`: 일부 앱에서 불필요한 팝업을 차단하거나 초기화 후 대기하도록 합니다.
    - `PYTHONPATH`: 공유 런타임(`dev-tools/Runtimes/Shared`)을 포함하도록 설정합니다.
3.  **앱 실행**: 각 앱의 카테고리에 맞는 Python 가상 환경(Conda)을 찾아 실행합니다.
4.  **창 감지 및 캡처**:
    - Win32 API를 사용하여 해당 프로세스의 가시적인 창 핸들(`HWND`)을 찾습니다.
    - 창을 최상단(`HWND_TOPMOST`)으로 가져온 후 `Graphics.CopyFromScreen`으로 영역을 캡처합니다.
5.  **종료 및 정리**: 캡처가 완료되면 프로세스와 하위 프로세스를 강제 종료합니다.

## 3. 사용 방법

### 전체 앱 캡처
```powershell
.\dev-tools\capture-python-gui-apps.ps1
```

### 특정 앱만 캡처 (테스트용)
```powershell
.\dev-tools\capture-python-gui-apps.ps1 -OnlyApps @("image_resizer") -WaitSeconds 15
```

### 파라미터 설명
- `-OnlyApps`: 캡처할 앱 ID 리스트
- `-WaitSeconds`: 창이 뜰 때까지 기다릴 최대 시간 (기본 20초)
- `-Categories`: 검색할 카테고리 리스트
- `-Clean`: 실행 전 이전 캡처 결과와 로그를 모두 삭제

## 4. 작동 테스트 결과 (2026-04-27)
`image/image_resizer` 앱을 대상으로 테스트를 진행한 결과, 정상적으로 작동함을 확인했습니다.

- **로그 기록**: `Diagnostics/gui_capture_log.md`
- **캡처 이미지**: `Diagnostics/gui_captures/image/image_resizer.png`

```
[2026-04-27T14:13:14] OK image/image_resizer | title=Image Resizer | class=Qt6110QWindowIcon | bounds=2535,690,3010,1703
```

## 5. 주의 사항
- **공유 런타임**: `dev-tools/Runtimes/Shared` 경로에 공유 런타임이 올바르게 연결되어 있어야 합니다.
- **창 포커스**: 캡처 시 창을 강제로 앞으로 가져오므로, 실행 중에는 마우스나 키보드 조작을 삼가야 정확한 캡처가 가능합니다.
