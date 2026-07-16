#!/usr/bin/env python3
"""Static validation harness for the Contexthub-Apps market repo.

Mirrors the category/app discovery algorithm used by package_apps.py
(top-level folders == categories, minus EXCLUDE_DIRS; an app is any
immediate subfolder of a category that contains a manifest.json) so that
findings line up with what actually ships into market.json.

Two severities:
  ERROR   -> exit code 1 (unless --strict is used, see below)
  WARNING -> printed, does not affect exit code by default

--strict promotes warnings to errors (both in the printed severity and in
the exit code). Not wired into CI yet -- see market-registry-check.yml.

Pure stdlib: json, os, re, sys, argparse.
"""
import argparse
import json
import os
import re
import sys

EXCLUDE_DIRS = {".git", ".github", "dist", "tmp", "venv", ".gemini", "node_modules"}
VALID_MODES = {"gui", "console", "background", "service"}
PYVER_RE = re.compile(r"^3\.\d+(\.\d+)?$")
# Lenient PEP-508-ish requirement line: name[extras] optionally followed by a
# version specifier / marker / URL, separated by one of <>=!~; or a space (@).
REQ_LINE_RE = re.compile(r"^[A-Za-z0-9._-]+(\[[A-Za-z0-9,._-]+\])?([<>=!~;@ ].*)?$")
# Categories that are known to never carry apps needing shared deps, or that
# are not Python-venv categories at all.
NO_CATEGORY_REQ_EXEMPT = {"native", "system", "comfyui", "dev-tools", "shared"}


class Finding:
    def __init__(self, severity, location, message):
        # severity: "ERROR" or "WARN"
        # location: a display string, e.g. "image/merge_to_exr" or "image"
        self.severity = severity
        self.location = location
        self.message = message

    def line(self, strict):
        sev = "ERROR" if (strict and self.severity == "WARN") else self.severity
        return f"[{sev}] {self.location}: {self.message}"


def discover_categories(root):
    categories = []
    for entry in sorted(os.listdir(root)):
        full = os.path.join(root, entry)
        if not os.path.isdir(full) or entry in EXCLUDE_DIRS:
            continue
        categories.append(entry)
    return categories


def discover_apps(root, category):
    cat_path = os.path.join(root, category)
    apps = []
    for entry in sorted(os.listdir(cat_path)):
        app_path = os.path.join(cat_path, entry)
        if not os.path.isdir(app_path):
            continue
        if not os.path.exists(os.path.join(app_path, "manifest.json")):
            continue
        apps.append(entry)
    return apps


def check_requirements_file(path, location, findings):
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
    except OSError as e:
        findings.append(Finding("ERROR", location, f"failed to read requirements.txt: {e}"))
        return
    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.lower() == "google-genai":
            findings.append(Finding(
                "ERROR", location,
                f"requirements.txt:{i}: 'google-genai' is not a real package; "
                f"did you mean 'google-generativeai'?"
            ))
            continue
        if not REQ_LINE_RE.match(s):
            findings.append(Finding(
                "ERROR", location,
                f"requirements.txt:{i}: line {s!r} does not look like a valid requirement"
            ))


def check_python_version_file(path, location, findings):
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read().strip()
    except OSError as e:
        findings.append(Finding("ERROR", location, f"failed to read python_version.txt: {e}"))
        return
    if not PYVER_RE.match(content):
        findings.append(Finding(
            "ERROR", location,
            f"python_version.txt content {content!r} does not match ^3\\.\\d+(\\.\\d+)?$"
        ))


def validate(root):
    findings = []
    all_ids = {}  # manifest id -> list of "category/app" locations (non-removed only)

    categories = discover_categories(root)

    for category in categories:
        cat_path = os.path.join(root, category)
        apps = discover_apps(root, category)

        # Category-level python_version.txt
        check_python_version_file(os.path.join(cat_path, "python_version.txt"), category, findings)

        # Category-level requirements.txt
        cat_req_path = os.path.join(cat_path, "requirements.txt")
        check_requirements_file(cat_req_path, category, findings)

        if apps and not os.path.exists(cat_req_path) and category not in NO_CATEGORY_REQ_EXEMPT:
            findings.append(Finding(
                "WARN", category,
                "category contains apps but has no category-level requirements.txt"
            ))

        # Empty category dir / only .gitkeep
        entries = os.listdir(cat_path)
        if len(entries) == 0 or (len(entries) == 1 and entries[0] == ".gitkeep"):
            findings.append(Finding("WARN", category, "category directory is empty or contains only .gitkeep"))

        for app in apps:
            location = f"{category}/{app}"
            app_path = os.path.join(cat_path, app)
            manifest_path = os.path.join(app_path, "manifest.json")

            try:
                with open(manifest_path, "r", encoding="utf-8-sig") as f:
                    manifest = json.load(f)
            except (OSError, ValueError) as e:
                findings.append(Finding("ERROR", location, f"manifest.json failed to parse: {e}"))
                continue

            if manifest.get("removed") is True:
                findings.append(Finding("WARN", location, "marked removed=true; folder can be deleted"))
                continue

            runtime = manifest.get("runtime") or {}
            execution = manifest.get("execution") or {}

            # 2. Required fields
            missing = []
            for field in ("id", "name", "version"):
                if not manifest.get(field):
                    missing.append(field)
            if not runtime.get("category"):
                missing.append("runtime.category")
            if not execution.get("entry_point"):
                missing.append("execution.entry_point")
            if not execution.get("mode"):
                missing.append("execution.mode")
            if missing:
                findings.append(Finding("ERROR", location, f"missing required field(s): {', '.join(missing)}"))

            # 3. execution.mode valid
            mode = execution.get("mode")
            if mode is not None and mode not in VALID_MODES:
                findings.append(Finding(
                    "ERROR", location,
                    f"execution.mode {mode!r} not in {sorted(VALID_MODES)}"
                ))

            # 4. runtime.category matches parent folder
            rt_category = runtime.get("category")
            if rt_category is not None and rt_category != category:
                findings.append(Finding(
                    "ERROR", location,
                    f"runtime.category {rt_category!r} != parent category folder {category!r}"
                ))

            # 5. entry_point exists
            entry_point = execution.get("entry_point")
            if entry_point and "${" not in entry_point:
                entry_full = os.path.join(app_path, entry_point)
                if not os.path.exists(entry_full):
                    findings.append(Finding("ERROR", location, f"entry_point {entry_point!r} does not exist"))

            # 6. manual.md required
            if not os.path.exists(os.path.join(app_path, "manual.md")):
                findings.append(Finding("ERROR", location, "manual.md missing"))

            # 7. duplicate id tracking (checked globally after the loop)
            mid = manifest.get("id")
            if mid:
                all_ids.setdefault(mid, []).append(location)

            # 11. manifest id == folder name (unless removed, already handled above)
            if mid and mid != app:
                findings.append(Finding("ERROR", location, f"manifest id {mid!r} != app folder name {app!r}"))

            # 8/9. app-level requirements.txt
            check_requirements_file(os.path.join(app_path, "requirements.txt"), location, findings)

            # 10. app-level python_version.txt
            check_python_version_file(os.path.join(app_path, "python_version.txt"), location, findings)

            # WARN: icon missing entirely
            has_png = os.path.exists(os.path.join(app_path, "icon.png"))
            has_ico = os.path.exists(os.path.join(app_path, "icon.ico"))
            if not has_png and not has_ico:
                findings.append(Finding("WARN", location, "no icon.png or icon.ico found"))

            # WARN: context_menu extensions not starting with "."
            triggers = manifest.get("triggers") or {}
            context_menu = triggers.get("context_menu") or {}
            for ext in context_menu.get("extensions") or []:
                if not str(ext).startswith("."):
                    findings.append(Finding(
                        "WARN", location,
                        f"context_menu extension {ext!r} does not start with '.'"
                    ))

    # 7. duplicate app id across the whole repo
    for mid, locations in all_ids.items():
        if len(locations) > 1:
            findings.append(Finding(
                "ERROR", locations[0],
                f"duplicate id {mid!r} also used by: {', '.join(locations[1:])}"
            ))

    # WARN: __pycache__ anywhere in the tree (should never be present/tracked)
    for dirpath, dirnames, _filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        if "__pycache__" in dirnames:
            rel = os.path.relpath(os.path.join(dirpath, "__pycache__"), root)
            findings.append(Finding("WARN", rel.replace(os.sep, "/"), "__pycache__ directory present"))

    return findings


def main():
    parser = argparse.ArgumentParser(description="Validate Contexthub-Apps market repo manifests/structure")
    parser.add_argument("--strict", action="store_true", help="Promote warnings to errors (not used in CI yet)")
    parser.add_argument("--root", default=".", help="Repo root to scan (default: current directory)")
    args = parser.parse_args()

    findings = validate(args.root)

    error_count = 0
    warn_count = 0
    for finding in findings:
        print(finding.line(args.strict))
        if args.strict and finding.severity == "WARN":
            error_count += 1
        elif finding.severity == "ERROR":
            error_count += 1
        else:
            warn_count += 1

    total = len(findings)
    print(f"\nvalidate_apps summary: {total} finding(s) -- {error_count} error(s), {warn_count} warning(s)"
          + (" [--strict]" if args.strict else ""))

    if error_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
