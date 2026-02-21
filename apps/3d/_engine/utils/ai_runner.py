import sys
import os
from pathlib import Path

def _setup_shims():
    # Find repository root (where Runtimes folder lives)
    current = Path(__file__).resolve()
    repo_root = None
    for parent in [current] + list(current.parents):
        if (parent / "Runtimes").exists() and (parent / "Apps_installed").exists():
            repo_root = parent
            break
    
    if not repo_root:
        return

    # Add Runtimes/Shared to sys.path
    shared_root = repo_root / "Runtimes" / "Shared"
    if shared_root.exists() and str(shared_root) not in sys.path:
        sys.path.insert(0, str(shared_root))

_setup_shims()

try:
    from contexthub.utils.ai_runner import *
except ImportError:
    pass
