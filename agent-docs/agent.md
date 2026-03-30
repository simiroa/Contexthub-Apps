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

Qt GUI 작업이면 아래 문서를 우선 본다.

1. `agent-docs/gui-runtime-contract.md`
2. `agent-docs/gui-runtime-status.md`
3. 대상 앱의 `manifest.json`
4. 대상 앱의 `main.py`
5. 대상 앱의 `manual.md`

- 앱/카테고리 목적: `agent-docs/app-overview.md`
- 운영 방식과 코드 위치: `agent-docs/architecture.md`
- 새 앱 추가 지침: `agent-docs/new-app-guidelines.md`
- Qt shared runtime 계약과 템플릿 분류: `agent-docs/gui-runtime-contract.md`
- 현재 템플릿 버킷과 위험 상태: `agent-docs/gui-runtime-status.md`
- 안정성 제약: `agent-docs/stability-constraints.md`
- Git 및 배포 정책: `agent-docs/git-policy.md`

## 4. 빠른 구조 요약

- 루트 카테고리: `3d`, `ai`, `ai_lite`, `audio`, `comfyui`, `document`, `image`, `utilities`, `video`
- `ai_lite`: 텍스트 유틸리티처럼 상대적으로 가벼운 AI 도구
- 현재 확인된 앱 수: 총 43개
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
- 공유 런타임을 수정했다면 `Contexthub\Runtimes\Shared` 원본 반영 여부까지 확인한다.
