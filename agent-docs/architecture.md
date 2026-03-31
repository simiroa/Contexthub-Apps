# Architecture And Code Locations

## 1. 최상위 구조

- `{category}/{app_id}/`: 실제 앱 단위
- `{category}/_engine/`: 같은 카테고리의 레거시 공용 엔진
- `{category}/requirements.txt`: 카테고리 공통 의존성
- `{category}/python_version.txt`: 카테고리 Python 기준 버전
- `{category}/external_libraries.txt`: 외부 바이너리 또는 도구 참고

## 1-1. 공통 데이터와 공용 자산 위치

카테고리별 `_engine` 아래에는 코드 외에도 공통 데이터가 들어간다.

- `core/`: 메뉴 라우팅, 경로 해석 같은 중심 로직
- `features/`: 실제 기능 스크립트
- `utils/`: GUI, 경로, 입력 처리, 이미지/AI 보조 유틸
- `setup/`: 모델 다운로드나 초기 설정 스크립트
- `manuals/`: 샘플 입력이나 내부 보조 자료
- `locales.json`: 카테고리 공용 로컬라이즈 문자열
- `history.json`: 최근 처리 이력 같은 공유 상태 파일
- `icon*.png`, `icon.ico`: 공용 아이콘 자산

## 2. 앱 실행 방식

많은 앱의 `main.py`는 직접 기능을 구현하지 않고 카테고리 `_engine` 내부 스크립트를 실행한다.

대표 패턴:

- `APP_ROOT`를 현재 앱 폴더로 잡는다.
- `LEGACY_ROOT`를 같은 카테고리의 `_engine`으로 잡는다.
- `runtime_bootstrap.resolve_shared_runtime()`로 shared/runtime 경로를 통일해서 계산한다.
- `CTX_APP_ROOT` 환경변수를 설정한다.
- 입력 파일을 CLI 인자, 헤드리스 입력, 파일 선택 대화상자에서 수집한다.
- `_engine/features/...` 아래 실제 GUI/기능 스크립트를 `runpy.run_path()`로 실행한다.

경로 계약은 앱별 하드코딩보다 환경변수와 공통 bootstrap을 우선한다.

- `CTX_APP_ROOT`: 현재 앱 루트
- `CTX_RUNTIME_ROOT`: 배포된 Contexthub Runtime 루트
- `CTX_DEV_RUNTIME_ROOT`: 개발용 로컬 runtime 미러 루트
- `CTX_SHARED_RUNTIME_ROOT`: shared runtime를 직접 주입해야 할 때 사용하는 선택 변수

앱 코드는 위 값을 직접 조합하지 말고 `runtime_bootstrap.py` 같은 공통 헬퍼를 통해 해석한다.

이 구조는 `image/image_convert/main.py`, `utilities/youtube_downloader/main.py` 같은 앱에서 확인된다.

Qt shared runtime의 공통 계약과 템플릿 분류는 `qt-app-builder-contexthub` 스킬을 기준으로 본다.

현재 shared Qt runtime 구현은 `dev-tools/runtime/Shared/contexthub/ui/qt/` 아래에서 토픽별로 분리되어 있다.

- `theme*`: palette, metrics, tone, stylesheet
- `support.py`: app icon/manual path, runtime preference helpers
- `widgets.py`: 공용 Qt 위젯
- `manual.py`: 매뉴얼 다이얼로그
- `header.py`: 헤더 surface
- `export_*`, `preview_*`, `queue_*`, `result_*`: 패널/표면 위젯
- `shell.py`, `panels*.py`: 기존 앱 import를 살리는 compatibility layer

새 작업은 가능하면 직접 모듈을 import하되, 기존 앱이 아직 의존하는 별칭은 recapture 이전에 제거하지 않는다.

## 3. 메타데이터 위치

- 루트 `market.json`: 마켓 전체 레지스트리
- 앱 `manifest.json`: 설치 후 런타임 메타데이터
- 앱 `manual.md`: 허브가 raw GitHub 경로에서 직접 읽는 문서

## 4. 패키징 및 배포 코드 위치

- 패키징 스크립트: `.github/scripts/package_apps.py`
- GitHub Actions: `.github/workflows/market-release.yml`
- 로컬 점검 배치: `test_locally.bat`
- 수동 푸시 보조: `git_push.bat`
- 배포 정책 참고: `gitguide.md`

## 5. package_apps.py 동작 요약

- 루트의 카테고리 폴더를 순회한다.
- 각 카테고리에서 `manifest.json`이 있는 하위 폴더를 앱으로 간주한다.
- 앱마다 `manual.md` 존재를 강제한다. 없으면 실패한다.
- 아이콘은 `icon.png` 우선, 없으면 `icon.ico`를 사용한다.
- 앱 폴더 전체를 `{id}.zip`으로 `dist/`에 압축한다.
- `market.json`을 다시 생성한다.

## 6. GitHub Actions 운영 방식

`main` 브랜치에 카테고리 폴더 변경이 푸시되면 배포 워크플로가 실행된다.

흐름:

1. 저장소 체크아웃
2. Python 설정
3. `package_apps.py`로 `dist/*.zip`과 `market.json` 생성
4. 변경된 `market.json` 커밋/푸시
5. 기존 `marketplace-latest` 릴리즈 삭제
6. 새 ZIP들로 `marketplace-latest` 릴리즈 재생성

## 7. 작업 시 위치별 책임

- 앱 기능 수정: 해당 앱 폴더 + 같은 카테고리 `_engine`
- 마켓 등록 문제 수정: `manifest.json`, `manual.md`, `icon`, `market.json`, 패키징 스크립트
- 배포 장애 수정: `.github/workflows/market-release.yml`, `.github/scripts/package_apps.py`

## 8. 카테고리 환경 판단 기준

- 공용 의존성이 이미 존재하면 기존 카테고리에 앱을 추가하는 편이 우선이다.
- `ai`, `image`, `document`처럼 카테고리 `requirements.txt`가 실질적으로 공통 런타임 역할을 한다.
- `ai` 카테고리는 추가로 Conda 우선 실행 규칙을 가진다.
  - 공유 런처는 `AI_CONDA_EXE`, `AI_CONDA_ENV_NAME`, `AI_CONDA_ENV_PATH` 설정을 참조한다.
  - 기본 모드는 `prefer_conda`이며, Conda/env 미검출 시 경고 후 현재 Python으로 fallback 한다.
  - 실제 AI 추론 스크립트 실행은 공유 `contexthub/utils/ai_runner.py` 쪽 해상도를 따른다.
- 새 카테고리를 만들 경우 최소한 다음 파일들을 함께 설계해야 한다.
  - `{category}/requirements.txt`
  - `{category}/python_version.txt`
  - `{category}/_engine/` 또는 독립 앱만 둘 명확한 이유
  - 대표 앱의 `manifest.json`, `main.py`, `manual.md`
