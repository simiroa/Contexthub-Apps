# Handoff: Qt GUI Design System 정리 — 실행 제안 + 에이전트 프롬프트

| Field | Value |
| --- | --- |
| **Date** | 2026-07-10 |
| **Status** | Ready to delegate |
| **Canonical design** | [`2026-07-10-qt-gui-design-system-simplification.md`](./2026-07-10-qt-gui-design-system-simplification.md) |
| **This file** | 구현 에이전트에 넘길 **실행 스펙 + 복붙 프롬프트** |
| **Primary repo** | `Contexthub-Apps` |
| **Product Shared** | Hub `Contexthub/Runtimes/Shared` |
| **Dev Shared** | `Contexthub-Apps/dev-tools/runtime/Shared` |

---

## 1. 한 줄 목표

**레이어를 더 얹지 말고**, 안 쓰는 패널/카탈로그/개념을 지우고, **색은 palette 한 경로**, **제품 Shared 정본은 Hub**, 로컬 개발만 Apps mirror를 쓰게 정리한다.

권고 전략: **Alternative B — Thin shell + optional components** (설계서 전문).

---

## 2. 잠긴 결정 (Phase 0 — 변경 금지)

| ID | 결정 |
| --- | --- |
| **Q1 / K13** | **Product SSOT** = Hub `Runtimes/Shared`. **Dev SSOT** = Apps `dev-tools/runtime/Shared`. Market ZIP에 Shared **미포함**. kit 동작 변경 PR은 Hub 반영 경로(링크/SHA) 없으면 미완료. |
| **Q3 / K18** | Accent = Hub **`#3A82FF`**. chip/soft/ManualDialog 등 accent-family rgba를 그 값에서 재계산. Apps palette → Hub 수렴. |
| **Q9 / K19** | Modularize = **Apps `shell.py` monolith extract only**. Hub 전체 맹목 복사 금지. |
| **Q11 / K20** | Hub `VideoPreviewCard` = **D1과 함께 삭제** (Apps caller 0). |
| **K2** | Shared `BaseAppWindow` / template base class **도입 금지**. |
| **K6 / K17** | Zero-caller panel 삭제 = **Apps + Hub 같은 릴리즈 트레인**. Apps PR에 **Hub delete SHA** 필수 (또는 Q2 예외 문서화). |

기본값 (설계서 잠금 보조):

- `ui.template` enum **유지** (태그/캡처용, 프레임워크 아님)
- `KIT_VERSION` 필드 **지금 안 넣음**
- `theme_contextup.json` **이번 프로그램 범위 밖**
- `fail-on-warning` 은 EXEMPT 축소 후에
- SystemC 토큰 시트는 필요 시 `agent-docs` 먼저

---

## 3. 정리 후 목표 상태 (How it will look)

### 3.1 개념 수

| Before (문제) | After (목표) |
| --- | --- |
| Catalog의 미구현 Card/Workspace 다수 | **실제 존재하는 API + recipe** 만 |
| full/compact/mini/special = “베이스 클래스 종류”처럼 읽힘 | **inventory/capture tag** 만 (`ui.template`) |
| palette + stylesheet 하드코딩 hex/rgba 이중 | **palette 모듈 단일 소유** (accent-family) |
| Apps 7파일 monolith vs Hub 30모듈 드리프트 | Apps extract 후 façade 유지; product=Hub |
| 0-caller 패널 5종 + VideoPreviewCard 잔존 | **삭제** (페어) |

### 3.2 새 앱 작성 기본 레시피 (미니 → 풀)

```text
1) main → engine Qt app
2) apply build_shell_stylesheet + HeaderSurface + apply_app_icon + attach_size_grip
3) mini:    selection summary + run_confirm_dialog (or single CTA)
4) compact: + FixedParameterPanel OR simple form (no multi list required)
5) full:    + ExportFoldoutPanel + FixedParameterPanel (+ PreviewList if needed)
6) special: shell 위 자유; raw hex 금지, EXEMPT만 예외 절차
7) set_*_role / get_shell_palette 로 강조색 — 앱 로컬 #hex 금지
```

### 3.3 Public kit surface (삭제하면 안 되는 것)

**Core (거의 모든 앱)**  
`build_shell_stylesheet`, `HeaderSurface`, `get_shell_palette`, `get_shell_metrics`, `apply_app_icon`, `attach_size_grip`, `run_confirm_dialog`, `set_surface_role` / `set_button_role` / `set_badge_role`, `refresh_runtime_preferences` / `runtime_settings_signature` (compat stubs)

**Common full/compact (mini 강제 금지)**  
`ExportFoldoutPanel`, `FixedParameterPanel`

**Optional (caller ≥1 — 유지)**  
`PreviewListPanel`, `AssetWorkspacePanel`, `ComparativePreviewWidget`, `CollapsibleSection`,  
`ElidedLabel`, `DropListWidget`, `get_shell_accent_cycle`, `set_transparent_surface`

**Delete (Apps + Hub 페어)**  
`ExportRunPanel`, `PresetParameterPanel`, `ParameterControlsPanel`, `QueueManagerPanel`, `ResultInspectorPanel`, Hub `VideoPreviewCard`

---

## 4. 작업 순서 (구체 제안)

구현 세션은 아래 **트랙 A → B** 순서를 지킨다. 설계서 PR 번호와 동일.

### Track A — 지금 막히지 않음 (Hub 결정 없이 시작 가능)

| Order | PR | 한 일 | 주 경로 | Done when |
| --- | --- | --- | --- | --- |
| 1 | **PR1** | 문서/카탈로그를 **라이브 surface**에 맞추고 phantom Card 제거; market count 28 반영 | `agent-docs/gui-runtime-contract.md`, `gui-runtime-status.md`, `qt-component-catalog.md`, `agent.md`, backlog | catalog에 없는 심볼 0; agent.md 앱 수=28 |
| 2 | **PR2** | theme contract CI | `.github/workflows/` 신규 또는 확장; `dev-tools/check-gui-theme-contract.py` | PR에서 ERROR 시 fail; 트리거가 `*_qt_*.py`만이 아닌 py/manifest/Shared 포함 |
| 3 | **PR5** | zero-caller 패널 삭제 (**Apps+Hub**) | Apps `dev-tools/runtime/Shared/contexthub/ui/qt/panels*.py`; Hub `.../ui/qt/*` | 양쪽 `rg`로 삭제 심볼 정의 0 (docs 제외); **Apps PR body에 Hub commit SHA** |
| 4 | **PR3-A** | checker 강화 stage A | `check-gui-theme-contract.py` | Shared `ui/qt/**` 스캔; allowlist = palette 후보 + **Apps 전체 shell.py**; deleted-panel import ban; template enum 검사(선택) |
| 5 | **PR8** | 새 앱 golden recipes | `new-app-guidelines.md`, templates | mini/compact/full/special → 실제 앱 id 매핑 |

### Track B — Phase 0 이미 잠김 → 순서만 지키면 됨

| Order | PR | 한 일 | Done when |
| --- | --- | --- | --- |
| 6 | **PR6** | palette 수렴 `#3A82FF` + ManualDialog/kit rgba 이전 | Apps↔Hub field matrix 일치; accent-family rgba palette 밖 0; capture set OK |
| 7 | **PR4b** | Apps `shell.py` **extract** (modularize) | façade import 깨지지 않음; K14 helpers 유지; capture set OK; 이후 PR3-B allowlist 축소 가능 |
| 8 | **PR7** | sync dry-run + SSOT diff 도구 | `ui/qt` allowlist only; palette/`__all__` drift exit code |
| 9 | **PR9** | EXEMPT 3종 burn-down (앱별 분리 PR 권장) | EXEMPT 수 감소 |
| 10 | **PR10** | `--fail-on-warning` CI | warnings=0 |

### Cross-repo D1 절차 (PR5 필수)

```text
1. Hub repo: delete ExportRunPanel / PresetParameterPanel / ParameterControlsPanel /
   QueueManagerPanel / ResultInspectorPanel / VideoPreviewCard modules + re-exports
2. Commit Hub; note SHA = HUB_D1_SHA
3. Apps repo: remove from panels.py / panels_*.py / __all__; ban in checker
4. Apps PR description MUST include: Hub D1 SHA = <hash>
5. rg both repos (exclude docs if needed) — zero definitions of deleted public names
6. Smoke: open 1 full + 1 mini app (local bootstrap)
```

Hub 접근 불가면: PR body에 **blocked on Hub** 명시하고 Apps만 docs/CI 진행. **삭제 PR을 Apps-only로 “완료” 처리하지 말 것.**

### Capture set (PR6 / PR4b 후)

- `audio_toolbox`, `doc_scan`, `auto_lod`, `extract_textures`, `creative_studio_advanced` 또는 `image_compare`, special smoke `versus_up`
- ManualDialog (`?` 버튼) 열어 third-accent 제거 확인

### 로컬 검증 명령

```powershell
cd Contexthub-Apps
python dev-tools/check-gui-theme-contract.py
# 이후 PR3부터:
# python dev-tools/check-gui-theme-contract.py --fail-on-warning   # PR10 전엔 선택
```

Hub 제품 경로 색 확인:

```powershell
$env:CTX_SHARED_RUNTIME_ROOT = "C:\Users\HG_maison\Documents\Contexthub\Runtimes\Shared"
# 그 다음 앱 로컬 실행 (dev-tools/run-app-local.ps1 등)
```

---

## 5. PR별 파일 체크리스트 (구현 시 채우기)

### PR1 — docs freeze
- [ ] `agent-docs/qt-component-catalog.md` → 실존 API + recipes only
- [ ] `agent-docs/gui-runtime-contract.md` → delete list / optional list / template=tag
- [ ] `agent-docs/gui-runtime-status.md` → 28앱 inventory, no removed apps
- [ ] `agent-docs/agent.md` (또는 동등) market count **43→28**
- [ ] two-plane SSOT 한 단락 (ZIP ≠ Shared)

### PR2 — CI
- [ ] workflow runs theme check on PR
- [ ] broad path triggers
- [ ] ERROR fails job

### PR5 — delete panels
- [ ] Apps code
- [ ] Hub code + SHA linked
- [ ] VideoPreviewCard Hub delete
- [ ] docs no longer advertise deleted panels as live

### PR3-A — checker
- [ ] scan Shared qt tree (not fully skip dev-tools Shared)
- [ ] staged allowlist documented in script header
- [ ] ban imports of deleted panels

### PR6 — palette
- [ ] Appendix D matrix applied
- [ ] ManualDialog `61,139,255` / `75,141,255` families gone or derived
- [ ] Hub chip_* matches final accent
- [ ] captures

### PR4b — extract
- [ ] `shell.py` split without façade break
- [ ] no Hub dead API copy
- [ ] captures

---

## 6. 범위 밖 (하지 말 것)

- 모든 special 앱 시각 전면 재디자인
- Demucs / AI 앱 통합
- SystemC WPF 전면 토큰 포팅 (이름 정렬 문서는 별도)
- market ZIP에 Shared 넣기 (설계 비권장; Q1 잠김)
- 0-caller 패널을 “나중에 쓸 수도” 이유로 유지

---

## 7. 성공 기준 (프로그램 Done)

- [ ] Catalog/contract = K14 live surface (panels + shell helpers)
- [ ] 삭제 패널 import 0 (app tree)
- [ ] Checker scans Shared with staged allowlist; eventual palette-only accent-family
- [ ] Apps+Hub D1 완료 + SHA 링크
- [ ] Apps↔Hub palette matrix equal after PR6
- [ ] accent-family raw rgba outside palette = 0 after PR3-C/PR6
- [ ] agent inventory count = 28
- [ ] CI theme ERROR fails PR
- [ ] kit behavior merges name Hub path (K13)

---

## 8. 다른 에이전트용 프롬프트 (복붙)

아래 블록 전체를 새 에이전트 세션 첫 메시지로 붙인다.  
`{HUB_ROOT}` 만 로컬 경로에 맞게 바꾼다.

````markdown
# Task: Implement Qt GUI Design System Simplification (Track A first)

## Role
You are an implementation agent for Contexthub-Apps. Follow the locked design; do not reopen Phase 0 product decisions. Prefer **delete complexity** over new abstractions.

## Canonical docs (READ FIRST, in order)
1. `agent-docs/designs/2026-07-10-qt-gui-design-system-simplification.md` — full design (Accepted, Phase 0 locked)
2. `agent-docs/designs/2026-07-10-qt-gui-design-handoff.md` — execution checklist and PR order
3. `agent-docs/gui-runtime-contract.md`, `gui-runtime-status.md`, `qt-component-catalog.md` (current contracts to update)

## Workspace
- Primary (edits): `Contexthub-Apps` (this repo)
- Product Shared (often required for D1/palette): `{HUB_ROOT}/Runtimes/Shared` e.g. `C:\Users\HG_maison\Documents\Contexthub\Runtimes\Shared`
- Dev Shared mirror: `dev-tools/runtime/Shared`

## Locked decisions (do not change)
- Product SSOT = Hub Shared; Dev = Apps mirror; market ZIP never ships Shared.
- Accent product = Hub `#3A82FF`; recompute chips/soft/ManualDialog accent-family from it (PR6).
- Modularize = extract Apps `shell.py` only; no blind Hub copy (PR4b).
- Delete zero-caller panels **paired Apps+Hub** with Hub SHA in Apps PR: ExportRunPanel, PresetParameterPanel, ParameterControlsPanel, QueueManagerPanel, ResultInspectorPanel, VideoPreviewCard.
- No new BaseAppWindow / shared template base classes.
- `ui.template` stays as inventory/capture tag only.

## Implementation order (Track A — do this first)
1. **PR1** — Docs freeze to live kit surface; remove phantom catalog Cards; fix market app count to 28; document two-plane SSOT.
2. **PR2** — CI: run `python dev-tools/check-gui-theme-contract.py` on PRs with broad path triggers; fail on errors.
3. **PR5** — Delete zero-caller panels in Apps + Hub (same train). Apps PR must link Hub commit SHA. Re-`rg` both trees.
4. **PR3-A** — Extend checker: scan Shared `contexthub/ui/qt/**`; staged allowlist = palette module + whole Apps `shell.py` for now; ban imports of deleted panels.
5. **PR8** — Agent recipes in new-app-guidelines / templates mapping mini|compact|full|special → real app examples.

Only after Track A is green, proceed Track B: **PR6** palette converge, **PR4b** shell extract, **PR7** sync dry-run, then EXEMPT burn-down / fail-on-warning.

## Working rules
- One logical PR (or one clear commit stack) at a time; stop after each PR with verification notes.
- Do not push unless asked.
- Do not commit pip junk under Diagnostics.
- If Hub repo is unavailable, stop PR5 deletion and report blocked; do not “finish” delete on Apps alone.
- After Shared behavior changes, note how Hub is updated (K13).
- Verify: `python dev-tools/check-gui-theme-contract.py` and spot-run one full + one mini app.

## Public surface must remain importable
Core: build_shell_stylesheet, HeaderSurface, palette/metrics getters, apply_app_icon, attach_size_grip, confirm dialog, set_*_role, runtime preference stubs.
Common: ExportFoldoutPanel, FixedParameterPanel.
Optional retain: PreviewListPanel, AssetWorkspacePanel, ComparativePreviewWidget, CollapsibleSection, ElidedLabel, DropListWidget, get_shell_accent_cycle, set_transparent_surface.

## Out of scope
Pixel redesign of all specials; AI app merges; putting Shared inside market ZIPs; inventing new heavy base classes.

## Deliverables per PR
- Diff limited to that PR’s files
- Short summary: what deleted/changed, how verified, Hub SHA if any
- Checklist against handoff §5 for that PR

Start with PR1 only. When PR1 is done and verified, wait for user confirmation before PR2 unless the user said “continue the full Track A”.
````

### 한 줄 버전 (짧은 위임)

```text
Contexthub-Apps에서 agent-docs/designs/2026-07-10-qt-gui-design-handoff.md 와 
2026-07-10-qt-gui-design-system-simplification.md 를 따른다. Phase 0 잠김.
Track A만: PR1 docs → PR2 CI → PR5 Apps+Hub panel delete(Hub SHA) → PR3-A checker → PR8 recipes.
BaseAppWindow 금지. 0-caller 패널 페어 삭제. Product Shared=Hub, accent=#3A82FF는 PR6.
PR1부터 하고 검증 후 멈춰라.
```

---

## 9. 위임 전 체크리스트 (사람)

- [ ] Hub 레포 경로 접근 가능 여부 (PR5 필수)
- [ ] 로컬이 `origin/main` 과 얼마나 어긋났는지 (`git status` / behind count) — 푸시 전 pull/rebase
- [ ] 이 handoff + design 문서가 커밋/푸시됐는지 (다른 에이전트 클론 기준)
- [ ] 위임 프롬프트에 `{HUB_ROOT}` 실경로 기입

---

## 10. 참고

- Design authoring temp (optional): `AppData/Local/Temp/grok-design-doc-219a56b8.md`
- Theme check: `dev-tools/check-gui-theme-contract.py`
- Packaging: `.github/scripts/package_apps.py` (app folder zip only)
