# Marketplace Distribution — Immutable-Safe Releases (A′)

**Date:** 2026-07-15
**Repo:** Contexthub-Apps (pipeline changes only; ContextHub host unchanged)
**Status:** Design approved pending user review

## Problem

The marketplace release pipeline (`.github/workflows/market-release.yml`) maintains a **single fixed-tag release** `marketplace-assets` and updates it each push via `gh release upload --clobber` (delete-then-upload). GitHub **immutable releases** is enabled on this repo, which makes published releases, their assets, and their tags permanent. Consequences observed:

- `--clobber` fails: `HTTP 422 Cannot delete asset from an immutable release`.
- Deleting the release is allowed, but **recreating a release with the same tag is not**: `tag_name was used by an immutable release`. The `marketplace-assets` tag is permanently burned.
- New app zips never reached the release, so some catalog apps (`ai_upscaler`, `image_enhancer`) had 404 download URLs.

Separately discovered gap (independent of immutability):

- Release zips contain **only the app folder** (`package_apps.py` zips `app_path`).
- Category shared files (`{category}/requirements.txt`, `python_version.txt`, `_engine/`) are **not delivered** to source-less end-users. `AppPayloadSynchronizer.SyncCategorySharedPayload` copies `AppsPath/category` → `AppsPath/category` (same path → no-op), so an end-user who only downloads an app zip gets no category-level Python requirements → env setup fails (e.g. missing PySide6).

## Goals

1. Release pipeline is **immutable-safe** — never mutates an existing release/tag; CI is green on every push.
2. **Host contract unchanged** — host still consumes `market.json` + an opaque `.zip` URL per app. No `ContextHub` (host) code changes.
3. **Stable download URLs** — `market.json` `zip_url` does not churn per release.
4. **Self-contained app bundles** — a source-less end-user can install and run an app from its zip alone.
5. Catalog **listing/refresh stays independent** of releases (already true; preserve it).

## Non-Goals

- Changing how the catalog is listed (market.json + raw icon/manual URLs already decoupled from releases).
- Eliminating GitHub Releases (end-user distribution requires a hosted bundle; opaque-URL releases keep host coupling minimal).
- Host-side install changes (explicitly avoided by choosing self-contained zips).

## Architecture

**Two independent planes, unchanged in spirit:**

- **Listing plane** — `market.json` (raw GitHub or local in dev) + icon/manual raw URLs. Drives catalog display and refresh. Independent of releases.
- **Install plane** — `zip_url` → download+extract an app bundle. Used only at install time.

**Contract (unchanged):** host knows only `market.json` schema + "a URL that returns an app `.zip`". It does not know how bundles are produced or hosted.

**Key mechanism — `/releases/latest/download/` + unique per-run tags:**

- Each CI run creates a **new release with a unique tag** (`assets-<run_number>`), uploads all app zips, and marks it `--latest`. Existing releases/tags are never touched → immutable-safe.
- `market.json` `zip_url` points to the **stable redirect** `https://github.com/<repo>/releases/latest/download/<app>.zip`, which GitHub always resolves to the newest release's asset. URLs never change → no market.json churn.

## Changes (Contexthub-Apps only)

### 1. `.github/scripts/package_apps.py`

- Change `release_url` from `…/releases/download/marketplace-assets` to
  **`https://github.com/{repo}/releases/latest/download`**.
  Each entry's `zip_url` becomes `{release_url}/{app_id}.zip` (stable).
- **Self-contained zips (category files):** when zipping an app, also include, under a predictable layout the host already understands, the app's category shared payload:
  - `{category}/requirements.txt`, `{category}/python_version.txt` (if present)
  - `{category}/_engine/` (if present)
  - The app folder itself (as today).
  - Layout note: the host extracts the zip into `AppsPath/{category}/{app_id}`. The category shared files must land at `AppsPath/{category}/…` (one level up). Resolve during implementation: either (a) the zip carries the app folder plus a sibling category-shared subtree and the host's existing extract path handles it, or (b) `SyncCategorySharedPayload` is confirmed to run from the bundled host `Apps/` and only the app folder is needed. **This layout detail is the one implementation risk to verify with a real end-user extract before finalizing.**
- `--check-only` behavior unchanged (zip_url is deterministic).

### 2. `.github/workflows/market-release.yml`

Replace the "Create/Update Release" step:

- Remove the `gh release view … && gh release upload --clobber` / `gh release edit` branch.
- New: compute `TAG=assets-${{ github.run_number }}`; `gh release create "$TAG" dist/*.zip --title "Marketplace Assets ($TAG)" --notes "…" --latest`.
- Keep: `package_apps.py` (full) → commit regenerated `market.json` (`[skip ci]`) → then create release.
- **Optional cleanup step** (nice-to-have): after creating the new release, delete `assets-*` releases older than the newest N (deletion is permitted; only same-tag recreation is not). Keeps the releases list tidy. Tags remain burned — that is fine because every run uses a fresh tag.

### 3. `.github/workflows/market-registry-check.yml`

- No change expected (zip_url is a fixed `/latest/download/` string; `--check-only` full-equality still holds). Verify during implementation.

### 4. Immediate restore / migration

- `marketplace-assets` release is already deleted and its tag burned.
- First run of the new workflow (or a one-time manual equivalent) creates `assets-<n>` with the current 26 app zips, marked `--latest`; `package_apps.py` repoints `market.json` to `/releases/latest/download/…`; commit + push. This restores all downloads.

## Testing / Verification

1. Run `package_apps.py --sync-registry-only` locally → confirm every `zip_url` uses `/releases/latest/download/`.
2. Run full `package_apps.py` → confirm each `dist/<app>.zip` contains the app folder **and** its category shared files.
3. Create a test release with a unique tag, mark `--latest`; confirm `https://github.com/<repo>/releases/latest/download/<app>.zip` resolves (200) and extracts to a runnable app on a machine **without** the source repo.
4. Push to main → confirm `market-release.yml` goes green (no 422) and `market-registry-check` passes.

## Open Items / Assumptions

- **A1 (must verify):** exact extract layout so category shared files land at `AppsPath/{category}/…`. If the host already ships category shells with its installer, option (i) may reduce to "just fix the release tag." Confirm before implementing the zip-contents change.
- **A2:** release accumulation over time — acceptable; optional cleanup step mitigates.
