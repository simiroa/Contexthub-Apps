import sys
import os

# Ensure we can import from the package
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from prompt_master.main import open_prompt_master
except ImportError:
    # Fallback if run from different context
    from .prompt_master.main import open_prompt_master

if __name__ == "__main__":
    if len(sys.argv) > 1:
        open_prompt_master(sys.argv[1])
    else:
        open_prompt_master()
