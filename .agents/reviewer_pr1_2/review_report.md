# Review Report

**Verdict**: APPROVE (with recommendations for PR1 documentation phase)
**Overall Risk Assessment**: LOW

---

## 1. Quality Review Findings

### [Major] Phrasing Ambiguity: Progressive Adoption Matrix Table
- **What**: The progressive adoption matrix table contains a potential source of misunderstanding regarding `BaseAppWindow` prohibition.
- **Where**: `agent-docs/designs/2026-07-10-qt-gui-design-system-simplification.md` (Line 373)
- **Why**: In the table, `BaseAppWindow` is only listed under the "Must not force" column for the `full` tier row. The rows for `mini` and `compact` list `panels` and `queue/result panels` in their "Must not force" columns, omitting `BaseAppWindow`.
- **Impact**: A reader might infer that the prohibition of `BaseAppWindow` applies exclusively to the `full` tier, or that it is acceptable to use a base window class in `mini`/`compact` layouts. According to the global decision `K2`, shared `BaseAppWindow` / template base classes are strictly prohibited across **all** application tiers.
- **Suggestion**: Add a note above or below the table, or add `BaseAppWindow` as a global constraint header to make it clear that the prohibition of shared base classes applies universally, not just to the `full` tier.

### [Minor] Phrasing Inconsistency: Special GUI description
- **What**: Unclear phrasing when describing base window restrictions for `special` apps.
- **Where**: `agent-docs/designs/2026-07-10-qt-gui-design-system-simplification.md` (Line 25)
- **Why**: The text states: *"special 앱은 heavy base를 강제하지 않는다."* (special apps do not force a heavy base).
- **Impact**: It might imply that non-special apps (e.g., `full`, `compact`, `mini`) do force or utilize a heavy base class.
- **Suggestion**: Revise this to: *"모든 앱 유형(full, compact, mini, special)에 대해 Shared `BaseAppWindow` 상속을 금지하고, stylesheet + HeaderSurface + 필요한 패널 구성의 composition 구조를 따른다."* (Prohibit shared BaseAppWindow inheritance across all app types...).

### [Minor] Terminology Synchronization: `ui.template` Role
- **What**: Concept gap between existing docs and new design docs on `ui.template` role.
- **Where**: `agent-docs/gui-runtime-status.md` and `agent-docs/gui-runtime-contract.md` vs. `agent-docs/designs/2026-07-10-qt-gui-design-system-simplification.md`
- **Why**: Existing docs describe `ui.template` as a choice for declaring structural/window buckets (e.g., "declaring structural specialness"). The new design strictly defines it as a metadata/inventory/capture tag only (`K3`), preventing it from driving runtime framework loading behavior.
- **Impact**: Can lead to developers attempting to load custom subclasses based on the manifest template tag.
- **Suggestion**: Ensure that PR1 (Docs freeze phase) explicitly updates `gui-runtime-contract.md` and `gui-runtime-status.md` to state that `ui.template` is purely for metadata/inventory/capture purposes and plays no part in runtime framework control.

---

## 2. Adversarial Review (Stress-Testing & Loophole Analysis)

### [Medium] Challenge 1: Loophole in Category-Local Template Carve-Out
- **Assumption Challenged**: Allowing `ui.template` to drive category-local layouts (`mesh_qt_shared.MeshModeSpec.template` -> size/layout) is safe and doesn't violate the prohibition of shared base window classes.
- **Attack Scenario**: An implementation developer bypasses the global `BaseAppWindow` prohibition by creating a heavy, centralized base window class within a specific category folder (e.g., `mesh/_engine/mesh_base_window.py`) and uses the `ui.template` metadata to dynamically resolve subclass structures locally.
- **Blast Radius**: Re-introduces the same concept bloat, code duplication, and class drift at the category level, eroding the goal of a simplified "Thin Shell + Optional Components" architecture.
- **Mitigation**: Update `new-app-guidelines.md` in PR8 to explicitly prohibit the creation of heavy, custom-templated base window classes even within category-local subdirectories. Local engines should also adhere to composition over inheritance.

---

## 3. Verified Claims

1. **Local Test Script Pass** -> Verified by executing `python dev-tools/check-gui-theme-contract.py` on the workspace tree.
   - *Result*: `Summary: errors=0 warnings=0 exemptions=3 fail_on_warning=no` -> **PASS**
2. **Markdown Syntax Validity** -> Verified by parsing structural tags, table formats, and Mermaid diagrams inside the 2 modified markdown files.
   - *Result*: All syntax formatting, headers, links, and Mermaid blocks (gantt, flowcharts) are well-formed. -> **PASS**

---

## 4. Conclusion (Korean)
**결론 및 요약**
최근 수정된 설계 문서인 `2026-07-10-qt-gui-design-handoff.md`와 `2026-07-10-qt-gui-design-system-simplification.md`는 공유 템플릿 베이스 클래스(`BaseAppWindow`)의 전면 금지 기조와 `ui.template`을 단순 인벤토리/캡처용 태그로만 제한하는 원칙을 일관되게 명시하고 있습니다. Markdown 문법 오류는 발견되지 않았으며 로컬 검사 스크립트도 성공적으로 통과하였습니다.

다만, 다음 세 가지 사항에 대해 미세한 모호함이나 개념 간극이 식별되었으므로 차후 PR1(문서 정비 단계) 및 PR8(가이드라인 수립 단계) 실행 시 반영할 것을 강력히 권장합니다:
1. **템플릿 매트릭스 표 표기 개선**: 점진적 적용 매트릭스 표에서 `BaseAppWindow` 금지가 오직 `full` 등급에만 해당되는 것처럼 오인되지 않도록 공통 금지 제약으로 명확히 표기해야 합니다.
2. **Special App 설명 문구 수정**: "special 앱은 heavy base를 강제하지 않는다"라는 서술을 "모든 앱 등급에서 heavy base 상속을 금지한다"로 수정하여 다른 등급의 오해 소지를 차단해야 합니다.
3. **로컬 우회(Loophole) 차단**: 카테고리 로컬 공유 파일(`mesh_qt_shared` 등)에서 `ui.template` 분기를 허용하는 예외 사항이, 실질적으로 카테고리 수준의 무거운 베이스 클래스 부활로 이어지지 않도록 가이드라인 수준에서 추가 제약을 명시해야 합니다.
