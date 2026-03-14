# Contexthub-Apps Agent Guide

이 저장소에서 작업하는 AI 에이전트는 먼저 `agent-docs/agent.md`를 읽고, 필요한 세부 규칙을 같은 폴더의 문서에서 추가로 확인한다.

Flet 포팅 작업이나 Flet 공용 UI 작업이면, 시작 문서는 `agent-docs/flet-migration-guidelines.md` 로 본다. 그 다음 `agent-docs/current-dev-context.md`, `agent-docs/templates/flet-porting-template.md`, 마지막으로 대상 앱 `manual.md` 를 읽는다.

핵심 원칙:

- 이 저장소는 Contexthub 앱 마켓용 미니앱 소스 모음이다.
- 앱은 카테고리별 폴더 아래 독립 앱 폴더로 배치된다.
- 각 앱은 `manifest.json`을 기준으로 식별되며, 배포 시 ZIP으로 패키징된다.
- 공통 동작은 카테고리별 `_engine`에 의존하는 경우가 많으므로, 기능 추가 전 반드시 앱 `main.py`와 같은 카테고리의 `_engine` 사용 여부를 확인한다.
- 배포 안정성에 직접 영향을 주는 파일은 `manifest.json`, `main.py`, `manual.md`, `icon.png|icon.ico`, `market.json`, `.github/scripts/package_apps.py`, `.github/workflows/market-release.yml` 이다.

세부 문서:

- `agent-docs/agent.md`
- `agent-docs/app-overview.md`
- `agent-docs/architecture.md`
- `agent-docs/new-app-guidelines.md`
- `agent-docs/current-dev-context.md`
- `agent-docs/gui-issue-playbook.md`
- `agent-docs/flet-migration-guidelines.md`
- `agent-docs/templates/README.md`
- `agent-docs/stability-constraints.md`
- `agent-docs/git-policy.md`
