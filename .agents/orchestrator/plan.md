# Execution Plan - PR1 Docs Freeze

## Objective
`agent-docs/designs/2026-07-10-qt-gui-design-handoff.md`의 PR1 명세에 맞추어 `agent-docs` 내 4개 문서(`qt-component-catalog.md`, `gui-runtime-contract.md`, `gui-runtime-status.md`, `agent.md`)를 정확하게 업데이트하고, PR1 완료 시점에서 작업을 멈추어 사용자 검증을 대기한다.

## Phased Plan

### Phase 1: Investigation (Explorer Dispatch)
- `teamwork_preview_explorer`를 소환하여 다음 사항을 분석:
  1. 현재 `agent-docs/qt-component-catalog.md`의 미구현 Card/Workspace 및 실존하는 API/레시피 상태.
  2. 현재 `agent-docs/gui-runtime-contract.md` 내용과 삭제/선택 목록, `template=tag` 정책 반영 상태.
  3. 현재 `agent-docs/gui-runtime-status.md` 내용과 Contexthub-Apps 내 전체 앱 개수 및 리스트(28개 앱 파악).
  4. 현재 `agent-docs/agent.md` 내 마켓 카운트 및 앱 수 표기 상태.
- Explorer는 구체적인 문서 수정 권장안(diff 계획)을 handoff.md에 담아 리포트한다.

### Phase 2: Implementation (Worker Dispatch)
- `teamwork_preview_worker`를 소환하여 Explorer의 권장안을 토대로 4개 문서를 실제로 수정하도록 지시한다.
- Worker가 직접 문서를 수정한다.

### Phase 3: Review & Verification (Reviewer & Auditor Dispatch)
- `teamwork_preview_reviewer`를 소환하여 수정된 문서의 일치성, 오타, 규칙 미준수 사항 등을 검토한다.
- `teamwork_preview_auditor`를 소환하여 Docs Freeze 요구사항이 온전히 이행되었는지(28개 앱 목록 정확성, market count 28 반영 등) 독립적으로 검증(Audit)한다.

### Phase 4: Final Synthesis & Pause
- 모든 결과를 종합하여 `progress.md`와 `plan.md`를 업데이트하고, 완료 메시지를 한국어로 작성하여 부모 에이전트와 사용자에게 보고한 뒤 대기 상태로 들어간다.
