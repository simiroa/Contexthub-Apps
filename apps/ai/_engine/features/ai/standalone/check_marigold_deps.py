"""
Check Marigold Dependencies Script
Called by Marigold GUI to verify models before running.
"""
import sys
import os
from pathlib import Path

# Setup paths to import utils/setup
SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
FEATURES_DIR = AI_DIR.parent
SRC_DIR = FEATURES_DIR.parent

sys.path.append(str(SRC_DIR))
sys.path.append(str(SRC_DIR / "setup"))

try:
    from utils import paths
    from setup.download_models import download_marigold
except ImportError:
    print("Error imports")
    sys.exit(1)

def main():
    print("Checking Marigold dependencies...")
    
    # We can just run the download_marigold function which handles checking/caching
    # It will verify if models exist in the standardized path.
    try:
        download_marigold()
        print("Success") # Keyword for GUI?
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    main()
