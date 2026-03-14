# New App Checklist

Before opening a PR or committing:

1. Replace `your_app_id`, `your_category`, and `Your App Name`
2. Point `SCRIPT_REL` to a real script under the category `_engine`
3. Set the correct `LEGACY_SCOPE`
4. Narrow `triggers.context_menu.extensions` to real supported inputs
5. Add `icon.png` or `icon.ico`
6. Rewrite `manual.md`
7. Run `python .github/scripts/package_apps.py`
