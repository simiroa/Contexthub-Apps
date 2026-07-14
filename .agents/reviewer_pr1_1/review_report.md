# Review Report & Adversarial Challenge

This report reviews the 4 modified files in `agent-docs/` (`qt-component-catalog.md`, `gui-runtime-contract.md`, `gui-runtime-status.md`, `agent.md`) against `agent-docs/designs/2026-07-10-qt-gui-design-handoff.md` and `ORIGINAL_REQUEST.md`.

---

## Review Summary

**Verdict**: REQUEST_CHANGES

## Findings

### Critical Finding 1: Phantom Components Not Removed from Catalog
- **What**: The conceptual "phantom" components (such as `InputCard`, `PreviewCard`, `StatusCard`, `QueueCard`, `QueueManagerCard`, `ExecutionCard`, `FullSplitWorkspace`, etc.) are still listed and detailed in `qt-component-catalog.md`.
- **Where**: `agent-docs/qt-component-catalog.md` (lines 40 to 174).
- **Why**: The design requirements (`2026-07-10-qt-gui-design-handoff.md` and `2026-07-10-qt-gui-design-system-simplification.md`) explicitly state that the catalog should only contain live/real API components and golden recipes, and that phantom components must be removed from the catalog. Keeping them causes confusion and documentation debt.
- **Suggestion**: Remove all unimplemented "Card" and "Workspace" components from `qt-component-catalog.md`. Limit the catalog to live components provided by the shared runtime (`HeaderSurface`, `PreviewListPanel`, `FixedParameterPanel`, `ExportFoldoutPanel`, `ComparativePreviewWidget`, `ConfirmDialog`, `CollapsibleSection`, `ElidedLabel`, `DropListWidget`, etc.).

### Critical Finding 2: Banned Panels Listed as Active
- **What**: Banned panels (`ExportRunPanel`, `PresetParameterPanel`, `ParameterControlsPanel`, `QueueManagerPanel`, `ResultInspectorPanel`) are listed under "Current Shared Runtime Coverage" and "Shared Runtime 계약" as active components, rather than being documented as deleted.
- **Where**: 
  - `agent-docs/gui-runtime-contract.md` (lines 60, 64-67)
  - `agent-docs/qt-component-catalog.md` (lines 224, 226-229)
- **Why**: According to Phase 0 locked decisions (D1), these zero-caller panels must be deleted from both Apps and Hub. Listing them as live and part of the contract contradicts the cleanup design.
- **Suggestion**: Document these panels as deleted/banned or remove them completely from the list of active shared runtime components.

### Major Finding 3: Inconsistent Market Count
- **What**: The total market count in `agent.md` is still documented as 43, whereas the design requires it to be consistently updated to 28.
- **Where**: `agent-docs/agent.md` (line 42)
- **Why**: The design states that the inventory must reflect the removal of market apps absorbed by SystemC media/av/pdf tools, bringing the total count to 28. Leaving the count at 43 causes inconsistency.
- **Suggestion**: Update line 42 of `agent.md` to state: "- 현재 확인된 앱 수: 총 28개".

### Critical Finding 4: Missing Two-Plane SSOT and Release Gate (K13) Documentation
- **What**: The Two-Plane SSOT concept (Hub Shared = Product original; Apps mirror = Dev/test original; ZIP does not ship Shared) and the Release Gate (K13) are not documented in the modified files.
- **Where**: `agent-docs/gui-runtime-contract.md`, `agent-docs/agent.md`
- **Why**: The design handoff specifically requires a paragraph explaining the Two-Plane SSOT (ZIP ≠ Shared) and the Release Gate (K13) to be documented as part of the docs freeze (PR1).
- **Suggestion**: Add a dedicated section or paragraph in `gui-runtime-contract.md` and `agent.md` explaining the Two-Plane SSOT concept and the K13 Release Gate requirement for any shared runtime behavior changes.

---

## Verified Claims

- Total count of apps in `gui-runtime-status.md` is 28 → verified via counting → **PASS**
- `check-gui-theme-contract.py` runs with zero errors/warnings → verified via execution → **PASS**

---

## Coverage Gaps

- **Lack of integration check for deleted panels** — risk level: **medium** — recommendation: Ensure the checker script is updated in subsequent PRs to ban imports of these deleted panels.

---

## Adversarial Challenge Report

## Challenge Summary

**Overall risk assessment**: HIGH (due to documentation mismatch that could lead implementation agents to write code using nonexistent or banned components).

## Challenges

### Critical Challenge 1: Implementation Drift from Outdated Docs
- **Assumption challenged**: Implementation agents will refer to `agent-docs` to find standard components.
- **Attack scenario**: An implementation agent or user looks at `qt-component-catalog.md` and tries to import/use `InputCard` or `QueueManagerCard` expecting them to be built-in shared runtime widgets. This will result in import/runtime errors or copy-paste duplication since these are phantom components.
- **Blast radius**: High. Breaks standard development flow and increases codebase duplication.
- **Mitigation**: Completely purge the phantom components from the catalog and leave only live APIs.

---

## 결론 (Conclusion)

현재 수정된 `agent-docs/` 내 4개 문서(`qt-component-catalog.md`, `gui-runtime-contract.md`, `gui-runtime-status.md`, `agent.md`)는 설계서(`2026-07-10-qt-gui-design-handoff.md`)의 요구사항을 충족하지 못하고 있습니다. 

1. **유령 컴포넌트(Phantom Components)**: `qt-component-catalog.md`에 실존하지 않는 개념적 카드/워크스페이스 컴포넌트들이 여전히 제거되지 않고 남아 있습니다.
2. **삭제 대상 패널(Banned Panels)**: 삭제 대상인 `ExportRunPanel`, `PresetParameterPanel` 등이 여전히 활성 라이브 컴포넌트로 기재되어 있습니다.
3. **마켓 앱 수 불일치**: `agent.md`에 총 앱 수가 28개가 아닌 기존 43개로 기재되어 있습니다.
4. **Two-Plane SSOT 및 K13 Release Gate 미기재**: 공통 계약 및 에이전트 매뉴얼 문서에 두 평면 SSOT(제품용 Hub Shared 원본 vs 개발용 Apps Shared 거울) 규칙과 K13 릴리즈 게이트 규칙이 문서화되어 있지 않습니다.

이에 따라 본 검토인은 **REQUEST_CHANGES** 판정을 내리며, 상기 미비점들을 보완할 것을 요청합니다.
