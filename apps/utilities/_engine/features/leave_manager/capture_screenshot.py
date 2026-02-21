import pyautogui
import time
import os
from pathlib import Path

# Wait a moment for window to be ready
time.sleep(0.5)

# Capture screenshot
screenshot = pyautogui.screenshot()

# Save to artifacts directory (or Desktop if not available)
base_dir = Path(os.path.expanduser("~")) / ".gemini" / "antigravity" / "brain"
if not base_dir.exists():
    base_dir = Path(os.path.expanduser("~")) / "Desktop"

output_path = base_dir / "vacance_redesign.png"
screenshot.save(output_path)

print(f"Screenshot saved to: {output_path}")
