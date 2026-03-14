# Git Policy

## 브랜치와 변경 범위

- 기본 배포 기준 브랜치는 `main`이다.
- 카테고리 폴더 변경이 `main`에 푸시되면 마켓 릴리즈 워크플로가 자동 실행된다.
- 따라서 실험성 변경과 배포 가능한 변경을 섞지 않는 것이 좋다.

## 커밋 정책

- 앱 변경 시 가능하면 앱 폴더 단위로 의미 있는 커밋을 만든다.
- 배포에 영향을 주는 메타데이터 변경은 앱 코드 변경과 분리하는 편이 안전하다.
- 자동 생성물은 원칙적으로 커밋하지 않는다. 예외는 루트 `market.json`처럼 배포 체인에서 관리되는 파일이다.

## 변경 후 점검

- 로컬에서 가능하면 `python .github/scripts/package_apps.py`로 패키징 검증
- 최소 확인 대상:
  - `manual.md` 누락 여부
  - ZIP 생성 성공 여부
  - `market.json` 엔트리 갱신 여부
  - 앱 `id`, `version`, `category` 정합성

## 릴리즈 정책

- 릴리즈 ZIP 파일명은 `{id}.zip`
- 릴리즈 태그는 `marketplace-latest`
- `market.json` 공개보다 ZIP 업로드/검증이 먼저라는 원칙을 지킨다.
- `id` 또는 `category` 변경 시 ZIP 이름, URL, 아이콘 경로, 매뉴얼 경로를 함께 검토한다.

## 하지 말아야 할 Git 작업

- 캐시, 로그, 모델, 런타임 DB, 사용자 데이터 커밋
- 앱 루트 밖의 임시 테스트 파일을 그대로 방치
- 배포 워크플로를 고려하지 않은 채 `market.json` 규칙을 임의로 수정

## 참고 파일

- 정책 요약: `gitguide.md`
- 패키징 로직: `.github/scripts/package_apps.py`
- 배포 워크플로: `.github/workflows/market-release.yml`
