# Immutable-Safe Release Pipeline (Plan 1) — Implementation Plan

> **For agentic workers:** implement task-by-task. Steps use `- [ ]` for tracking.

**Goal:** Make the marketplace release pipeline immutable-safe (fix the 422 failures, green CI, stable download URLs) and make downloaded app zips self-sufficient for Python packages (category requirements merged in), all in the Contexthub-Apps repo with **zero host code changes**.

**Architecture:** Each CI run creates a NEW release with a unique tag (`assets-<run_number>`) marked `--latest`; `market.json` `zip_url` points to the stable `…/releases/latest/download/<app>.zip` redirect. `package_apps.py` merges each app's category-level `requirements.txt`/`python_version.txt` into the app zip so a source-less install gets category packages (e.g. PySide6). The host contract (market.json + opaque zip URL) is unchanged.

**Tech Stack:** Python 3.x (`package_apps.py`), GitHub Actions YAML, `gh` CLI.

**Scope note:** Deferred to a later plan — delivery of category-level `_engine/` shared *code* to source-less end-users (packages are covered here; `_engine` is a smaller, app-specific concern and there are no end-users yet).

---

### Task 1: `package_apps.py` — stable `/latest/download/` URL

**Files:**
- Modify: `.github/scripts/package_apps.py:12`

- [ ] **Step 1: Change `release_url`**

Replace line 12:
```python
    release_url = f"https://github.com/{repo}/releases/download/marketplace-assets"
```
with:
```python
    release_url = f"https://github.com/{repo}/releases/latest/download"
```
(The `zip_url` at line ~91 — `f"{release_url}/{zip_name}"` — then becomes `…/releases/latest/download/<app>.zip`, unchanged otherwise.)

- [ ] **Step 2: Verify URL shape**

Run: `python .github/scripts/package_apps.py --sync-registry-only`
Then: `grep '"zip_url"' market.json | head -1`
Expected: URL contains `/releases/latest/download/` and ends `<app_id>.zip`.

---

### Task 2: `package_apps.py` — merge category requirements into app zips

**Files:**
- Modify: `.github/scripts/package_apps.py` (packaging block, lines ~70-81)

**Context:** Today the zip is built by `os.walk(app_path)` writing every file with arcname relative to `app_path`. We must (a) NOT write the app's own `requirements.txt` verbatim, (b) write a MERGED `requirements.txt` = category `requirements.txt` + app `requirements.txt` (dedup, comments/blank lines dropped), and (c) if the app has no `python_version.txt`, include the category's. Applies ONLY to the real packaging path (not `--sync-registry-only`/`--check-only`), so `market.json` content is unaffected.

- [ ] **Step 1: Add a merge helper near the top of the file (after imports)**

```python
def _read_requirement_lines(path):
    lines = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8-sig') as rf:
            for raw in rf:
                s = raw.strip()
                if s and not s.startswith('#'):
                    lines.append(s)
    return lines

def _merged_requirements(category_path, app_path):
    """Category requirements first, then app-specific, de-duplicated (case-insensitive)."""
    merged, seen = [], set()
    for req in (os.path.join(category_path, 'requirements.txt'),
                os.path.join(app_path, 'requirements.txt')):
        for line in _read_requirement_lines(req):
            key = line.lower()
            if key not in seen:
                seen.add(key)
                merged.append(line)
    return merged
```

- [ ] **Step 2: Rewrite the packaging block to inject merged requirements + category python_version**

Replace the existing packaging block (the `if not sync_registry_only and not check_only:` that does `os.walk` and `zipf.write`) with:

```python
            if not sync_registry_only and not check_only:
                print(f"Packaging {app_id} v{version}...")
                merged_reqs = _merged_requirements(category_path, app_path)
                app_pyver = os.path.join(app_path, "python_version.txt")
                cat_pyver = os.path.join(category_path, "python_version.txt")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for sub_root, sub_dirs, sub_files in os.walk(app_path):
                        for file in sub_files:
                            # Skip the app's own requirements.txt; we write a merged one below.
                            if sub_root == app_path and file == "requirements.txt":
                                continue
                            file_full_path = os.path.join(sub_root, file)
                            arcname = os.path.relpath(file_full_path, app_path)
                            zipf.write(file_full_path, arcname)
                    # Merged requirements (category + app) so source-less installs get category packages.
                    if merged_reqs:
                        zipf.writestr("requirements.txt", "\n".join(merged_reqs) + "\n")
                    # If the app has no python_version.txt, fall back to the category's.
                    if not os.path.exists(app_pyver) and os.path.exists(cat_pyver):
                        with open(cat_pyver, 'r', encoding='utf-8-sig') as pf:
                            zipf.writestr("python_version.txt", pf.read())
```

- [ ] **Step 2b: Confirm `category_path` is in scope**

`category_path` is defined earlier in the loop as `os.path.join(".", category)` (existing code ~line 29). No new variable needed. If the local name differs, use the existing category-folder path variable.

- [ ] **Step 3: Verify merged zip contents**

Run: `rm -rf dist && python .github/scripts/package_apps.py`
Then inspect an image-category app (image category `requirements.txt` lists PySide6):
```bash
python -c "import zipfile; z=zipfile.ZipFile('dist/merge_to_exr.zip'); print(z.read('requirements.txt').decode())" | grep -i pyside6
```
Expected: `PySide6` present in the merged requirements.txt inside the zip.
Also: `python -c "import zipfile; print('requirements.txt' in zipfile.ZipFile('dist/merge_to_exr.zip').namelist())"` → `True`, and no duplicate `requirements.txt` entries.

- [ ] **Step 4: Verify market.json unchanged by the merge**

Run: `python .github/scripts/package_apps.py --check-only`
Expected: `Success: market.json is perfectly in sync.` (merge affects zip bytes only, not registry entries.)

---

### Task 3: `market-release.yml` — unique-tag release (immutable-safe)

**Files:**
- Modify: `.github/workflows/market-release.yml:53-68` (the "Create/Update Release" step)

- [ ] **Step 1: Replace the Create/Update Release step**

Replace the whole `- name: Create/Update Release` step (lines 53-68) with:

```yaml
      - name: Create Release (immutable-safe, unique tag)
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TAG="assets-${{ github.run_number }}"
          gh release create "$TAG" dist/*.zip \
            --title "Marketplace Assets ($TAG)" \
            --notes "Auto-generated marketplace bundles (run ${{ github.run_number }}, ${{ github.sha }})." \
            --latest

      - name: Prune old asset releases (keep newest 5)
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release list --limit 100 --json tagName,createdAt \
            --jq '[.[] | select(.tagName | startswith("assets-"))] | sort_by(.createdAt) | reverse | .[5:] | .[].tagName' \
          | while read -r tag; do
              [ -n "$tag" ] && gh release delete "$tag" --yes || true
            done
```

Rationale: never mutates an existing release/tag (each run uses a fresh `assets-<run_number>` tag), so GitHub immutable releases can never 422. Pruning deletes old *releases* (allowed); their tags stay burned (harmless — future runs use new tags).

- [ ] **Step 2: Lint check (YAML valid)**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/market-release.yml'))"`
Expected: no error.

---

### Task 4: `market-registry-check.yml` — confirm still valid

**Files:**
- Inspect: `.github/workflows/market-registry-check.yml` (no change expected)

- [ ] **Step 1: Confirm `--check-only` still passes with the new URL scheme**

Run: `python .github/scripts/package_apps.py --check-only`
Expected: `Success: market.json is perfectly in sync.`
(The check regenerates registry entries with the same `release_url`, so the committed `/latest/download/` URLs match. No workflow edit needed. If it fails, regenerate with `--sync-registry-only` and commit.)

---

### Task 5: Immediate restore + commit + push (orchestrator-run)

**Files:** `market.json` (regenerated), `.github/scripts/package_apps.py`, `.github/workflows/market-release.yml`

- [ ] **Step 1: Regenerate registry + build zips**

Run: `python .github/scripts/package_apps.py --sync-registry-only` (repoints market.json to /latest/download/)
Then: `rm -rf dist && python .github/scripts/package_apps.py` (builds merged zips)
Expected: `dist/*.zip` count == market.json app count.

- [ ] **Step 2: Create an immediate `--latest` release so `/latest/download/` resolves now**

Run: `gh release create "assets-restore-$(git rev-parse --short HEAD)" dist/*.zip --title "Marketplace Assets (restore)" --notes "Manual restore after immutable-tag migration." --latest`
Expected: release created; `gh release view <tag> --json isLatest --jq .isLatest` → true.

- [ ] **Step 3: Commit and push the pipeline changes + regenerated market.json**

```bash
git add .github/scripts/package_apps.py .github/workflows/market-release.yml market.json docs/superpowers
git commit -m "feat(market): immutable-safe release pipeline + self-contained app zips"
git push origin main
```

- [ ] **Step 4: Verify the push-triggered workflow is green and downloads resolve**

- `gh run list --workflow market-release.yml --limit 1` → latest run `completed/success` (no 422).
- `curl -sL -o /dev/null -w "%{http_code}" https://github.com/simiroa/Contexthub-Apps/releases/latest/download/merge_to_exr.zip` → `200`.

---

## Self-Review Notes
- Spec coverage: immutable-safe release (Tasks 3,5) ✓; stable URL (Task 1) ✓; self-contained packages (Task 2) ✓; check workflow (Task 4) ✓; restore/migration (Task 5) ✓. `_engine` code delivery explicitly deferred.
- Placeholder scan: none — all steps contain concrete code/commands.
- Type/name consistency: `_merged_requirements`, `_read_requirement_lines`, `category_path`, `app_path`, `app_id`, `zip_path` match existing/added names.
