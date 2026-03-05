import webbrowser
import sys
import time
from pathlib import Path

# Add src to path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from manager.helpers.comfyui_service import ComfyUIService
from utils.i18n import t

def main():
    print(t("comfyui.dashboard.server_status"))
    service = ComfyUIService()
    ok, port, started = service.ensure_running(start_if_missing=True)
    if not ok:
        print(t("comfyui.common.not_available"))
        port = 8190
    elif started:
        time.sleep(2)

    url = f"http://127.0.0.1:{port}"
    print(f"Opening {url}...")
    webbrowser.open(url)

if __name__ == "__main__":
    main()
