
import sys
import os
from pathlib import Path

# Identify Project Root (assuming this file is in src/utils)
# src/utils -> src -> Root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src"

def setup():
    """
    Ensures 'src' is in sys.path.
    This function is called automatically on import if possible, 
    but strictly speaking, the import itself usually requires path setup first.
    """
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
        # print(f"[Bootstrap] Added {SRC_DIR} to sys.path")

# Auto-run setup on import
setup()
