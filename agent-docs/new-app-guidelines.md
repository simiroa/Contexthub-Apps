# New App Guidelines

## 1. 우선 판단: 기존 카테고리 vs 새 카테고리

새 앱을 만들 때는 먼저 기존 카테고리 안에 넣을 수 있는지 판단한다.

기존 카테고리에 넣는 편이 좋은 경우:

- 입력 타입이나 작업 도메인이 기존 카테고리와 같다.
- 기존 `_engine/features/...` 안에 재사용 가능한 기능이 있다.
- 카테고리 공통 의존성으로 충분하다.
- 마켓에서 사용자가 같은 종류의 도구로 인식하는 것이 자연스럽다.

새 카테고리가 필요한 경우:

- 의존성 묶음이 기존 카테고리와 충돌하거나 지나치게 다르다.
- 공통 UI/공용 유틸/공유 데이터 구조를 새로 묶는 편이 장기적으로 낫다.
- 작업 도메인이 기존 분류와 명확히 다르다.

## 2. 새 앱 최소 구성

앱 폴더는 최소 다음 구성을 권장한다.

- `{category}/{app_id}/manifest.json`
- `{category}/{app_id}/main.py`
- `{category}/{app_id}/manual.md`
- `{category}/{app_id}/icon.png` 또는 `icon.ico`
- `{category}/{app_id}/requirements.txt` 필요 시

배포 안정성 관점에서 `manual.md`는 사실상 필수다.

바로 시작할 때는 템플릿을 바로 복제하기보다, 앱 유형을 먼저 판단한다.
새 PySide6 Qt 앱이면 사용자 skill 라이브러리의 `qt-app-builder-contexthub`를 우선 기준으로 본다.
legacy wrapper 계열이면 `agent-docs/templates/new-app-template/`를 검토한다.

## 3. 권장 개발 방식

- 가장 가까운 기존 앱 폴더를 복제해 시작한다.
- `main.py`는 가능하면 현재 저장소의 래퍼 패턴을 유지한다.
- 앱 전용 로직이 작으면 앱 폴더 안에 둔다.
- 여러 앱이 재사용할 기능은 카테고리 `_engine/features` 또는 `_engine/utils`로 올린다.
- 사용자 설정, 이력, 샘플 데이터가 공용이면 `_engine` 쪽에 둔다.
- GUI 앱이면 먼저 `qt-app-builder-contexthub` 스킬과 `agent-docs/gui-runtime-status.md`를 보고 템플릿 버킷을 정한다.
- 새 Qt 앱은 가능하면 기존 앱 복제보다 `qt-app-builder-contexthub`의 템플릿 자산을 시작점으로 삼는다.

## 4. main.py 권장 패턴

기존 저장소는 다음 패턴을 자주 사용한다.

- `APP_ROOT`와 `LEGACY_ROOT` 계산
- `CTX_APP_ROOT` 환경변수 설정
- 파일/폴더 입력 수집
- 헤드리스 모드 분기
- `_engine/features/...` 스크립트 실행

이 패턴을 유지하면 카테고리 공통 GUI, 경로, 입력 보조 로직을 재사용할 수 있다.

## 5. manifest.json 작성 기준

- `id`: ZIP 이름과 마켓 식별자의 기준이 되므로 안정적으로 유지
- `runtime.category`: 실제 폴더 카테고리와 일치
- `runtime.python_version`: 카테고리 기준과 맞춤
- `execution.entry_point`: 보통 `main.py`
- `triggers.context_menu.extensions`: 실제 처리 가능한 확장자만 명시
- `ui.framework`: 기존 카테고리와 맞추는 편이 안전함
- `ui.template`: `full`, `compact`, `mini`, `special` 중 하나를 명시하면 상태 분류와 캡처 규칙이 쉬워짐

확장자를 과하게 넓히면 잘못된 파일이 앱으로 열릴 수 있다.

## 6. 카테고리별 공통 환경

현재 확인된 공통 패턴:

- 대부분 `python_version.txt`는 `3.11`
- `ai/requirements.txt`: AI 추론용 대형 의존성 묶음
- `ai` 카테고리 실행은 이제 Conda 환경 우선 기준으로 본다.
  - 기본 설정은 `AI_ENV_MODE=prefer_conda`
  - 기본 env 이름은 `contexthub-ai`
  - `AI_CONDA_EXE`, `AI_CONDA_ENV_NAME`, `AI_CONDA_ENV_PATH`로 조정 가능
  - Conda가 없거나 env를 찾지 못하면 경고 후 기존 Python으로 fallback
- `image/requirements.txt`: 이미지/EXR/벡터라이즈 처리 의존성
- `document/requirements.txt`: PDF, OCR, 문서 변환 의존성
- `video/requirements.txt`: 현재는 `customtkinter` 중심의 가벼운 구성
- `comfyui/requirements.txt`: `customtkinter`, `Pillow`, `pygame`, `requests`

새 앱이 기존 카테고리에 들어가면 이 공통 환경과 충돌하지 않는지 먼저 본다.

AI 앱 추가 시 추가 확인:

1. 새 기능이 `contexthub-ai` Conda 환경 기준으로 돌아가는지 확인
2. `pip` 자동 설치 코드를 넣기 전에 Conda 패키지 전략과 충돌하지 않는지 확인
3. 모델 다운로드/외부 바이너리/torch 계열은 Conda env 안에서 경로가 닫히는지 확인

## 7. 공통 데이터와 리소스 배치 규칙

앱 폴더에 둘 것:

- 앱 고유 아이콘
- 앱별 안내 문서
- 앱 하나만 쓰는 얇은 진입점
- 앱 하나만 쓰는 소규모 설정/리소스

카테고리 `_engine`에 둘 것:

- 여러 앱이 함께 쓰는 GUI 라이브러리
- 공통 메뉴/라우팅
- 입력 처리 보조
- 공통 아이콘/테마/로케일
- 공유 이력 파일 또는 샘플 입력

## 8. 새 카테고리 생성 체크리스트

1. 새 카테고리명이 기존 분류와 겹치지 않는지 확인
2. `{category}/requirements.txt` 작성
3. `{category}/python_version.txt` 작성
4. `{category}/_engine/` 필요 여부 결정
5. `_engine`를 만든다면 `core`, `features`, `utils` 최소 구조 준비
6. 대표 앱 하나에 `manifest.json`, `main.py`, `manual.md`, 아이콘 준비
7. `package_apps.py`가 별도 수정 없이 앱을 인식하는지 확인
8. 로컬에서 패키징 검증

새 카테고리의 초기 뼈대는 `agent-docs/templates/new-category-template/`를 기준으로 잡는다.

## 9. 새 앱 추가 전후 체크리스트

추가 전:

1. 기존 카테고리 재사용 가능성 검토
2. 유사 앱의 `main.py`와 `manifest.json` 확인
3. 처리 대상 확장자와 실행 모드 정의

추가 후:

1. `manual.md` 누락 여부 확인
2. 아이콘 존재 확인
3. `python .github/scripts/package_apps.py` 실행
4. 생성된 `market.json` 엔트리 확인
5. ZIP 내부 구조 확인

## 10. 권장하지 않는 방식

- 카테고리 공통 로직을 새 앱마다 복붙
- `_engine` 공통 자산을 앱 폴더마다 중복 보관
- `manifest.json`의 카테고리, 폴더 위치, 실제 기능 범위가 서로 불일치
- 새 카테고리를 만들면서 공통 환경 파일 없이 앱만 추가
