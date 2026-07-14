# Git Repository Status and BaseAppWindow Conflict Analysis

## Executive Summary
This analysis addresses the divergence between our local `main` branch (which is ahead by 3 commits and behind by 25 commits relative to `origin/main`) and the design rules defined in PR1. Specifically, it details the conflict where `origin/main` has merged commits implementing `BaseAppWindow` migrations, whereas local design rule K2 strictly prohibits `BaseAppWindow`, and provides a concrete synchronization strategy and contract update proposal to resolve this drift.

---

## 1. Repository Status & Conflict Breakdown

### Local vs. Remote Git Status
- **Local Status**: Ahead by 3 commits, behind by 25 commits relative to `origin/main`.
- **Local Commits (Ahead)**:
  - `fc04356 docs(gui): add design-system execution handoff and agent prompt`
  - `5ea9400 docs(gui): accept Qt design system simplification (Phase 0 locked)`
  - `487e866 Remove market apps absorbed by SystemC media/av/pdf tools`
- **Remote Commits (Behind)**:
  - `819a55d refactor(phase2b-cleanup): migrate 7 divergent qt_apps to BaseAppWindow`
  - `1f4d0d9 refactor(phase2): consolidate headless_inputs (9 copies) + BaseAppWindow (10 apps)`
  - These commits migrated 17 active apps to inherit from a shared `BaseAppWindow` class (defined in `shared/_engine/runtime/base_window.py` on the remote).

### The Conflict (Rule K2 vs. origin/main Codebase)
- **Local Design Rule K2**: Prohibits shared `BaseAppWindow` or template base classes globally across all application tiers to prevent tight coupling.
- **Current Remote Implementation**: Already contains `BaseAppWindow` and has migrated 17 apps to it.
- **Nature of Conflict**: Synchronizing with `origin/main` will pull in the `BaseAppWindow` framework and migrations, contradicting the absolute rule K2 defined in the design docs.
- **Resolution Principle**: Treat the remote `BaseAppWindow` implementation as a **temporary architectural drift**. The design rule K2 remains active, meaning no new code may use `BaseAppWindow`, and existing usages are frozen and scheduled for refactoring/removal in future PRs (such as Track B).

---

## 2. Proposed Git Synchronization Strategy

To update the local branch while preserving the local PR1 documentation changes, the worker should follow a rebase-based workflow.

### Git Commands for the Worker
```powershell
# Step 1: Stash uncommitted local changes (docs and market.json)
git stash -u

# Step 2: Fetch the latest commits from the remote repository
git fetch origin

# Step 3: Rebase local commits on top of the latest remote branch
git rebase origin/main

# Step 4: Re-apply local changes on top of the rebased branch
git stash pop
```

### Conflict Resolution for `market.json`
Since both remote and local branches may have modified `market.json`, a conflict is highly likely when popping the stash.
- **Resolution**:
  1. During `git stash pop`, if `market.json` conflicts, checkout the remote version to clean the state:
     ```powershell
     git checkout --theirs market.json
     ```
  2. Regenerate `market.json` locally using the packaging script to ensure it is in sync with the actual 28 active apps:
     ```powershell
     python .github/scripts/package_apps.py
     ```
  3. Verify that the market registry is correct and clean:
     ```powershell
     git diff market.json
     ```

---

## 3. Proposed Documentation Update (Contract Files)

To align the codebase status with the design contract, we propose adding a **Divergence Note** under the **K2 Rule** in `agent-docs/gui-runtime-contract.md`.

### Proposed Diff for `agent-docs/gui-runtime-contract.md`

```markdown
<<<< BEFORE (Lines 80-85)
## K2: Base Class Prohibition Rule

- **Prohibit shared BaseAppWindow / template base classes globally across all application tiers.**
- 모든 애플리케이션 계층에서 공통 `BaseAppWindow`나 템플릿 기반의 공유 base class 사용을 완전히 금지한다.
- 각 앱은 런타임에서 로드되는 표준 윈도우 클래스를 가지거나 독립적으로 윈도우를 작성해야 하며, 상속을 통한 암묵적인 레이아웃 공유나 기능 공유 패턴을 배제하여 강한 결합을 원천 차단한다.
====
## K2: Base Class Prohibition Rule

- **Prohibit shared BaseAppWindow / template base classes globally across all application tiers.**
- 모든 애플리케이션 계층에서 공통 `BaseAppWindow`나 템플릿 기반의 공유 base class 사용을 완전히 금지한다.
- 각 앱은 런타임에서 로드되는 표준 윈도우 클래스를 가지거나 독립적으로 윈도우를 작성해야 하며, 상속을 통한 암묵적인 레이아웃 공유나 기능 공유 패턴을 배제하여 강한 결합을 원천 차단한다.

### [Divergence Note / 임시 예외 및 전이 상태 공지]
- **현상**: 원격 저장소(`origin/main`)의 최근 리팩토링 단계(커밋 `1f4d0d9`, `819a55d` 등)에서 17개의 기존 Qt 앱들이 `BaseAppWindow`를 상속받도록 병합되었습니다.
- **규칙 (동결)**: Rule K2에 따라, 새로운 코드 및 신규 앱 작성 시 `BaseAppWindow` 상속 및 추가 도입은 **엄격히 금지(Frozen/Prohibited)**됩니다.
- **향후 계획**: 현재 코드베이스에 적용된 `BaseAppWindow` 관련 상속 패턴은 과도기적 드리프트(temporary drift)로 간주되며, 이후 정렬 단계(Track B 등)에서 완전히 제거하고 개별 앱의 독립적 구조로 리팩토링될 예정입니다.
>>>> AFTER
```

---

## 4. Conclusion (결론)

**요약 및 권장 사항**:

1. **저장소 동기화**: 로컬 브랜치의 문서 변경 사항을 안전하게 보존하면서 원격 저장소(`origin/main`)의 최신 리팩토링 사항을 반영하기 위해 `git stash` -> `git fetch` -> `git rebase origin/main` -> `git stash pop` 순서로 동기화를 진행할 것을 권장합니다. 특히 `market.json` 충돌 발생 시 원격 버전을 기준으로 복구한 뒤 `python .github/scripts/package_apps.py` 스크립트를 재구동하여 로컬 환경에 맞게 마켓 파일을 갱신해야 합니다.
2. **설계 상충 문서화**: 원격 코드베이스에 이미 적용된 `BaseAppWindow` 마이그레이션과 로컬 K2 규칙(`BaseAppWindow` 도입 금지) 간의 일시적 불일치를 해결하기 위해, `agent-docs/gui-runtime-contract.md` 파일의 K2 규칙 하단에 **임시 예외 및 전이 상태 공지(Divergence Note)**를 명시합니다. 이를 통해 현재 구현된 코드는 일시적인 전이 상태(drift)이며 신규 코드에서의 추가 상속은 완전히 동결(frozen)되었고 향후 제거될 예정임을 분명히 선언합니다.
