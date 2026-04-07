# Legacy Generic Template

이 폴더는 과거 `_engine` 스크립트를 얇게 감싸는 범용 앱 템플릿이다.

## Status

- Qt 전용 시작점이 아니다.
- `customtkinter` 또는 legacy wrapper 흐름과 가까운 일반 템플릿으로만 본다.
- 새 PySide6 Qt 앱 생성에는 사용하지 않는다.

## Do Not Use This For

- 새 `pyside6` GUI 앱
- `mini`, `compact`, `full`, `special` 템플릿 버킷이 필요한 앱
- shared runtime shell/palette/panel 기반으로 시작해야 하는 앱

## Use Instead

- 사용자 skill 라이브러리의 `qt-app-builder-contexthub`
- `qt-app-builder-contexthub` 스킬 문서
- `agent-docs/gui-runtime-status.md`

## Still Valid For

- legacy `_engine` 스크립트를 감싸는 얇은 런처
- GUI 계약이 없는 일반 starter
- category-specific wrapper를 빠르게 복제해야 하는 경우
