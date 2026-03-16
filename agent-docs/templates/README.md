# Templates

이 폴더는 새 앱 또는 새 카테고리를 만들 때 복제해서 시작하는 템플릿 모음이다.

## 포함 템플릿

- `new-app-template/`: 기존 카테고리 안에 새 앱을 추가할 때 사용하는 기본 템플릿
- `new-category-template/`: 새 카테고리를 만들 때 사용하는 최소 골격
- `flet-porting-template.md`: 기존 GUI 앱을 Flet으로 옮길 때 사용하는 구조/체크리스트 템플릿
- `qt-template/`: shared Qt runtime 기반 패널형 앱을 복제해서 시작하는 템플릿

Qt 템플릿을 쓸 때는 먼저 `agent-docs/qt-shared-runtime-guidelines.md`를 읽는다.

## 사용 원칙

- 템플릿은 실제 앱이 아니다. 그대로 배포 대상에 넣지 않는다.
- 복제 후 앱 ID, 카테고리명, 스크립트 경로, 트리거, 확장자를 반드시 바꾼다.
- 아이콘 파일은 템플릿에 바이너리로 넣지 않았으므로 복제 후 `icon.png` 또는 `icon.ico`를 직접 추가한다.

## 권장 순서

1. 가장 가까운 기존 앱과 템플릿을 비교해 시작점 결정
2. 템플릿 복제
3. `manifest.json`, `main.py`, `manual.md` 수정
4. 필요 시 카테고리 `_engine`에 공통 기능 추가
5. `python .github/scripts/package_apps.py`로 검증
