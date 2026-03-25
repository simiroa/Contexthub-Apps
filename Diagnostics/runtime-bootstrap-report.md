# Runtime Bootstrap Report

## 요약

현재 저장소의 앱 래퍼들은 대체로 `runtime_bootstrap.resolve_shared_runtime()`를 사용하도록 정리됐지만, 작업이 길어진 이유는 앱마다 경로 주입 관례가 달라서 동일한 문제를 반복해서 수정해야 했기 때문이다.

## 확인 결과

- `main.py` 기준으로 `runtime_bootstrap` 사용 앱은 41개다.
- `main.py`에서 `dev-tools/runtime/Shared` 또는 `Contexthub/Runtimes`를 직접 하드코딩하는 패턴은 정리됐다.
- 남아 있는 직접 경로 표기는 대부분 `runtime_bootstrap.py` 자체, 문서, 또는 `__pycache__`다.
- 실제 소스 리스크는 더 이상 “경로 하드코딩”이 아니라, `_engine` 내부의 기능 코드가 `CTX_APP_ROOT` 또는 shared runtime 계약을 어떻게 소비하는지로 옮겨갔다.

## 왜 끝이 안 보였는가

1. 래퍼 계약이 없었다.
   - 같은 `main.py`라도 앱마다 `os.chdir`, `sys.path`, shared runtime fallback 순서가 달랐다.
2. 템플릿이 통일되지 않았다.
   - 새 앱 샘플이 옛 방식이면 정리한 규칙이 다시 퍼진다.
3. 문서가 늦게 따라왔다.
   - 코드만 고치면 다음 작업자가 다른 패턴을 정답으로 오해한다.
4. 레거시 Flet 제거와 Qt 정리가 동시에 진행됐다.
   - 런타임 계약 문제와 UI 전환 문제가 섞여서, 겉보기에는 계속 새 이슈처럼 보였다.

## 현재 남은 리스크

- `_engine` 내부 서비스 코드가 앱별로 `CTX_APP_ROOT`를 소비하는 방식이 미세하게 다를 수 있다.
- `main.py`가 정리돼도, 일부 서비스 함수는 자체적인 경로 계산을 계속할 수 있다.
- `__pycache__`와 진단 로그에는 옛 패턴 문자열이 남아 있을 수 있다.

## 권장 다음 단계

1. `_engine` 내부에서 `CTX_APP_ROOT`, `CTX_RUNTIME_ROOT`, `CTX_DEV_RUNTIME_ROOT`를 직접 읽는 파일만 별도 목록화한다.
2. `runtime_bootstrap.py`를 공식 계약으로 고정하고, 새 앱 템플릿을 이 규칙만 따르도록 유지한다.
3. 경로 이슈가 끝나면 그 다음에 GUI 기능 회귀와 UI 진입점 검사를 진행한다.
