"""
Central path management for ContextUp.
All path constants should be imported from here to ensure consistency.
"""
from pathlib import Path

def _resolve_root() -> Path:
    import os
    env_root = os.environ.get("CTX_ROOT")
    if env_root:
        return Path(env_root)

    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "config").exists() and (parent / "Apps_installed").exists():
            return parent
    # Fallback: repo root is four levels up from Apps_installed/image/_engine/core
    return current.parents[4]

# Root directory (ContextHub/)
ROOT_DIR = _resolve_root()

# ============================================================
# App Configs (git managed)
# ============================================================
CONFIG_DIR = ROOT_DIR / "config"
TIERS_FILE = CONFIG_DIR / "install_tiers.json"
MENU_CATEGORIES_DIR = CONFIG_DIR / "categories"

# ============================================================
# User Data (git excluded - sensitive/personal data)
# ============================================================
USERDATA_DIR = ROOT_DIR / "userdata"
SETTINGS_FILE = USERDATA_DIR / "settings.json"
SECRETS_FILE = USERDATA_DIR / "secrets.json"
USER_OVERRIDES_FILE = USERDATA_DIR / "user_overrides.json"
GUI_STATES_FILE = USERDATA_DIR / "gui_states.json"
COPY_MY_INFO_FILE = USERDATA_DIR / "copy_my_info.json"
INSTALL_PROFILE_FILE = USERDATA_DIR / "install_profile.json"
DOWNLOAD_HISTORY_FILE = USERDATA_DIR / "download_history.json"

# ============================================================
# Logs directory
# ============================================================
LOGS_DIR = ROOT_DIR / "logs"

# ============================================================
# Source & Assets
# ============================================================
SRC_DIR = ROOT_DIR / "src"
ASSETS_DIR = ROOT_DIR / "assets"

# ============================================================
# Tools directory
# ============================================================
TOOLS_DIR = ROOT_DIR / "tools"
PYTHON_DIR = TOOLS_DIR / "python"
SCRIPTS_DIR = SRC_DIR / "scripts"


def ensure_userdata_dir():
    """Create userdata directory if not exists."""
    USERDATA_DIR.mkdir(exist_ok=True)


def migrate_engine_userdata():
    """
    Migrate user data files from legacy config/ location to userdata/.
    Called during installation to preserve existing user settings.
    """
    import shutil
    
    migrations = [
        (CONFIG_DIR / "settings.json", SETTINGS_FILE),
        (CONFIG_DIR / "secrets.json", SECRETS_FILE),
        (CONFIG_DIR / "user_overrides.json", USER_OVERRIDES_FILE),
        (CONFIG_DIR / "gui_states.json", GUI_STATES_FILE),
        (CONFIG_DIR / "copy_my_info.json", COPY_MY_INFO_FILE),
        (CONFIG_DIR / "install_profile.json", INSTALL_PROFILE_FILE),
        (CONFIG_DIR / "download_history.json", DOWNLOAD_HISTORY_FILE),
        (CONFIG_DIR / "runtime" / "gui_states.json", GUI_STATES_FILE),
        (CONFIG_DIR / "runtime" / "download_history.json", DOWNLOAD_HISTORY_FILE),
    ]
    
    ensure_userdata_dir()
    migrated = []
    
    for old_path, new_path in migrations:
        if old_path.exists() and not new_path.exists():
            try:
                shutil.move(str(old_path), str(new_path))
                migrated.append(old_path.name)
            except Exception as e:
                print(f"[WARN] Failed to migrate {old_path.name}: {e}")
    
    if migrated:
        print(f"[INFO] Migrated user data: {', '.join(migrated)}")
    
    return migrated
