# Original User Request

## Initial Request — 2026-07-10T09:07:11Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

Contexthub-Apps 리포지토리의 Qt GUI Design System Simplification 설계서 및 핸드오프 문서에 명시된 규칙을 준수하여 Track A 구현을 시작합니다. 

Working directory: C:\Users\HG_maison\Documents\Contexthub-Apps
Integrity mode: development

## Requirements

### R1. PR1(Docs Freeze) 최우선 진행
`agent-docs/designs/2026-07-10-qt-gui-design-handoff.md` 문서의 8. "다른 에이전트용 프롬프트" 및 PR 계획을 준수하여 PR1(문서 업데이트) 작업을 수행합니다. PR1 작업 완료 시 반드시 진행을 멈추고 사용자에게 보고하여 검증을 받아야 합니다.

### R2. Phase 0 제약사항 준수
- Product Shared=Hub, Dev=Apps mirror 기조 유지
- BaseAppWindow 또는 공유 템플릿 베이스 클래스 도입 금지
- PR5 진행 시 0-caller 패널은 Apps와 Hub 양쪽에서 삭제해야 하며, Hub가 없는 환경에서는 맹목적인 삭제 완료 처리 금지 (반드시 Hub SHA 링크 포함)
- pip junk(진단성 임시 패키지/파일) 커밋 금지 및 코드 푸시는 명시적인 사용자 요청 시에만 실행

### R3. Track A 순차 진행
작업은 반드시 Track A의 명시된 순서(PR1 docs → PR2 CI → PR5 delete → PR3-A checker → PR8 recipes)대로 진행되어야 하며, PR1 결과 검증 전에는 다음 PR로 넘어가지 않습니다.

## Acceptance Criteria

### PR1 완료 기준
- [ ] `agent-docs/qt-component-catalog.md` 파일이 실제 존재하는 API와 레시피만 포함하도록 수정되었다.
- [ ] `agent-docs/gui-runtime-contract.md` 파일에 삭제 대상 목록, 선택적 목록, template=tag 정책이 올바르게 명시되었다.
- [ ] `agent-docs/gui-runtime-status.md` 파일에 제거된 앱 없이 28개 앱 인벤토리가 정확히 반영되었다.
- [ ] `agent-docs/agent.md` 문서의 마켓 카운트가 43에서 28로 수정되었다.
- [ ] 위의 PR1 작업 완료 직후, 추가 작업 없이 에이전트가 대기 상태로 전환되며 완료를 보고한다.
