# Contexthub-Apps AI Agent Manual

## 1. 이 저장소의 목적

이 저장소는 `Contexthub`라는 별도 앱에서 설치하고 실행하는 미니앱들의 소스 저장소다. 사용자는 `market.json`에 등록된 앱을 선택해 설치하며, 실제 앱 번들은 GitHub Release ZIP으로 제공된다.

즉, 이 저장소의 목적은 다음 두 가지다.

- 카테고리별 미니앱 소스를 관리한다.
- 배포 가능한 앱 마켓 메타데이터와 ZIP 산출물을 안정적으로 만든다.

## 2. 에이전트의 기본 작업 원칙

- 기능 추가 전 먼저 해당 앱의 `manifest.json`, `main.py`, `manual.md`를 읽는다.
- 앱이 단독 구현인지, 카테고리 공용 `_engine` 위임 구조인지 먼저 판단한다.
- 배포 흐름에 영향이 있는 변경이면 `market.json` 생성 규칙과 GitHub Actions 흐름까지 함께 확인한다.
- 런타임 캐시, 모델, 로그, 사용자 데이터는 소스 저장소에 포함하지 않는다.
- 사용자가 명시하지 않은 기존 구조 변경은 피하고, 현재 카테고리 패턴을 유지한다.

## 3. 먼저 읽을 문서

Qt GUI 작업이면 아래 문서와 스킬을 우선 본다.

1. `qt-app-builder-contexthub` 스킬의 `SKILL.md` 및 `references` 문서
2. `agent-docs/gui-runtime-status.md`
3. 대상 앱의 `manifest.json`
4. 대상 앱의 `main.py`
5. 대상 앱의 `manual.md`

- 앱/카테고리 목적: `agent-docs/app-overview.md`
- 운영 방식과 코드 위치: `agent-docs/architecture.md`
- 새 앱 추가 지침: `agent-docs/new-app-guidelines.md`
- Qt shared runtime 계약과 템플릿 분류: `qt-app-builder-contexthub` 스킬 참조
- 현재 템플릿 버킷과 위험 상태: `agent-docs/gui-runtime-status.md`
- 안정성 제약: `agent-docs/stability-constraints.md`
- Git 및 배포 정책: `agent-docs/git-policy.md`

## 4. 빠른 구조 요약

- 루트 카테고리: `3d`, `ai`, `ai_lite`, `audio`, `comfyui`, `document`, `image`, `legacyapp`, `native`, `system`, `utilities`, `video`
- `ai_lite`: 텍스트 유틸리티처럼 상대적으로 가벼운 AI 도구
- 앱 기본 단위: `{category}/{app_id}/`
- 공통 엔진: `{category}/_engine/`
- 배포 스크립트: `.github/scripts/package_apps.py`
- 배포 워크플로: `.github/workflows/market-release.yml`

## 5. 수정 우선순위

1. 앱 동작 변경: 앱 폴더와 같은 카테고리 `_engine`을 함께 점검
2. 메타데이터 변경: `manifest.json`, `manual.md`, 아이콘 경로 점검
3. 배포 변경: 패키징 스크립트와 워크플로를 함께 검토

## 6. 새 앱 개발 시 추가 원칙

- 먼저 기존 카테고리 안에 넣을 수 있는지 검토하고, 새 카테고리는 공통 엔진이나 공용 의존성이 정말 분리돼야 할 때만 만든다.
- 가능하면 같은 카테고리의 기존 앱 `main.py` 패턴을 복제해 시작한다.
- 공통 데이터, 리소스, 헬퍼는 앱 폴더보다 카테고리 `_engine`에 둘 수 있는지 먼저 판단한다.
- 앱 추가 전 `agent-docs/new-app-guidelines.md`를 읽고 구조를 맞춘다.

## 7. 금지에 가까운 행동

- `_engine` 의존 앱을 단순 독립 앱처럼 수정하지 않는다.
- `manual.md` 없이 앱을 추가하거나 유지하지 않는다.
- 캐시, 모델, 출력물, DB, 로그를 커밋하지 않는다.
- 릴리즈 경로와 `market.json` 규칙을 무시한 임의 배포 구조를 만들지 않는다.

## 8. 현재 작업 기준점

- Python GUI 공통 규격은 shared Qt runtime 계약과 카테고리 `_engine` 패턴을 우선한다.
- 템플릿 분류는 `full`, `compact`, `mini`, `special` 4버킷 기준으로 본다.
- 앱별 분류는 실제 인터랙션 구조를 우선하고, `manifest.json`의 `ui.template`를 최종 선언값으로 맞춘다.
- GUI 이슈 수정 후에는 `dev-tools/capture-python-gui-apps.ps1`로 캡처 회귀 확인을 우선한다.
- `ai` 카테고리 실행은 이제 Conda 우선 규칙을 가진다.
  - 기본 모드: `prefer_conda`
  - 기본 env 이름: `contexthub-ai`
  - Conda 미설치 또는 env 미검출 시 경고 후 기존 Python으로 fallback
- 공유 런타임을 수정했다면 실제 원본인 `C:\Users\HG\Documents\Contexthub\Runtimes\Shared` 반영 여부까지 확인한다.
- 저장소 내부 개발 기준 경로는 `dev-tools/Runtimes` 심볼릭 링크다. `dev-tools/runtime_Old`는 레거시 수동 미러로만 취급하고, 참조가 모두 정리되기 전까지 제거하지 않는다.
- shared Qt runtime은 `dev-tools/Runtimes/Shared/contexthub/ui/qt`를 기준으로 작게 나뉜 모듈 구조를 유지하되, 기존 앱 호환용 별칭과 래퍼는 캡처로 검증되기 전까지 유지한다.
- 공유 이름을 제거할 때는 관련 앱을 다시 캡처해서 실제 실행이 살아 있는지 먼저 확인한다.
- `legacyapp/ai/qwen3_tts`, `legacyapp/ai/whisper_subtitle`는 이름과 달리 아직 활성 앱 루트다. 이번 단계에서는 삭제 대상이 아니라 보관 대상이다.

## 9. 로컬 개발 환경 vs 허브 런타임 환경 (Local Dev vs Hub Runtime)

앱 개발 및 디버깅 시 파이썬 환경의 차이를 명확히 인지해야 한다. 에이전트가 에러의 원인을 오판하지 않도록 주의한다.

- **허브 런타임 (배포 환경)**:
  사용자가 허브에서 앱을 실행할 때, 허브 코어가 해당 카테고리 전용 가상환경(env)을 만들고 `{category}/requirements.txt`에 명시된 패키지(예: `PySide6`)를 자동 설치해 준다.
- **로컬 개발 (IDE 환경)**:
  이 저장소 자체는 파이썬 의존성을 격리해 들고 있지 않다. `main.py`를 직접 실행할 때 `ModuleNotFoundError: No module named 'PySide6'` 에러가 발생한다면, **코드 경로 버그가 아니라 현재 로컬 인터프리터에 패키지가 없는 것**이다. 로컬 터미널에서 수동으로 패키지를 설치해야 앱 윈도우를 띄울 수 있다.
- **런타임 소스코드 결합 (Bootstrapping)**:
  `shared/_engine` 이나 공용 템플릿 컴포넌트(`shared/_engine/components`) 파일들을 파이썬이 찾는 과정은 전적으로 앱의 `main.py` 초기 설정에 달렸다. 따라서 `main.py` 최상단에서 의존성 모듈을 바로 임포트하지 말고, `runtime_bootstrap.py`를 통해 `sys.path` 조립이 완전히 끝난 이후에 **지연 임포트(Lazy Import)** 방식으로 UI를 로드해야 환경에 관계없이 안전하게 코드를 찾는다.

## 10. GUI 테스트 및 검증 원칙 (에이전트 행동 지침)

AI 에이전트가 리팩토링이나 코드 수정을 완료한 후, 터미널 환경에서 스스로 테스트하기 위해 낭비하는 시간을 줄이기 위해 다음 사항을 철저히 지킨다.

- **로컬에서 직접 스크립트 실행 금지**: 에이전트는 `run_command` 도구를 사용하여 UI 파일(`.py`)을 터미널에서 직접 실행하거나 팝업을 띄우는 테스트를 시도해서는 안 된다. 
- **`contexthub` 모듈 경로 탐색 금지**: 터미널 기반 실행 시 `ModuleNotFoundError: No module named 'contexthub'` 등의 프레임워크 래퍼 모듈 누락 에러가 발생하더라도, 이는 에이전트의 워크스페이스 터미널의 `PYTHONPATH` 문제일 뿐 실제 오류가 아니다. 불필요한 경로(Path) 탐색 명령이나 환경 변수 수정을 통해 파헤치려 시도해선 안 된다.
- **테스트는 사용자에게 위임**: 코드가 논리적으로 완성되었다고 판단되면, 에이전트 환경에서 억지로 작동시키려 하지 말고 사용자에게 "외부 런타임(Contexthub 앱 환경)을 통해 GUI 테스트를 직접 수행해 달라"고 요청하라.
