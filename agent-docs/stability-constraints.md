# Stability Constraints

## 절대 우선 제약

- 앱 식별 기준은 폴더명이 아니라 `manifest.json` 존재 여부와 내부 `id`다.
- 배포 성공 기준에는 `manual.md` 존재가 포함된다.
- 허브는 `market.json`의 `zip_url`, `icon_url`을 그대로 사용한다.
- 허브의 매뉴얼 경로는 사실상 `main/{category}/{id}/manual.md` 규칙에 묶여 있다.

## 구조 보존 규칙

- 앱 루트에는 최소한 `manifest.json`, `main.py`, `manual.md`를 유지한다.
- ZIP 내부에서 `manifest.json`을 찾기 어려운 깊은 중첩 구조를 만들지 않는다.
- 카테고리별 `_engine` 내부 경로를 바꿀 때는 이를 참조하는 앱 `main.py` 전부를 함께 검토한다.
- `manifest.json`의 `id`, 카테고리 폴더명, ZIP 파일명, `market.json` 엔트리는 서로 정합해야 한다.

## 코드 수정 시 제약

- `_engine` 사용 앱에서 실행 스크립트 상대경로(`SCRIPT_REL`)를 바꾸면 실제 파일 존재를 검증한다.
- `LEGACY_SCOPE`에 따라 입력 수집 방식이 달라지므로, 컨텍스트 메뉴 앱을 백그라운드 앱처럼 바꾸지 않는다.
- `CTX_APP_ROOT` 사용을 제거하거나 깨뜨리지 않는다. 앱별 리소스 참조가 끊길 수 있다.
- GUI 앱은 인자 미선택 시 경고 후 종료하는 현재 UX를 함부로 바꾸지 않는다.

## 저장소 청결 규칙

- 커밋 금지: `__pycache__/`, `*.pyc`, `logs/`, `userdata/`, `*.db`, `*.sqlite`, `dist/`, `build/`, `tmp/`, `temp/`, `.venv/`, `venv/`
- 커밋 금지: 모델/허브 캐시(`hf/`, `hub/`, `blobs/`, `snapshots/`, `models--*/`)
- 커밋 금지: 생성 산출물(`frames/`, `outputs/`, `checkpoints/`, `weights/`)
- 민감정보, 로컬 절대경로, 계정정보, API 키를 소스에 남기지 않는다.

## 변경 전에 확인할 항목

1. 이 앱이 `_engine` 위임형인지 독립형인지
2. `manual.md`, 아이콘, `manifest.json`이 모두 존재하는지
3. 변경이 `market.json` 생성 결과에 영향을 주는지
4. 카테고리 공통 의존성 파일과 충돌하는지
