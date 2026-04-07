import sys

from core.logger import setup_logger
from manager.helpers.comfyui_service import ComfyUIService

logger = setup_logger("comfy_server_utils")


def is_comfy_running(port=8190):
    """Check if ComfyUI server is responding on the given port."""
    service = ComfyUIService(port=port)
    running, _ = service.is_running()
    return running


def start_comfy(port=8190):
    """Start ComfyUI server in the background if not running."""
    service = ComfyUIService(port=port)
    ok, used_port, started = service.ensure_running(start_if_missing=True)
    if ok:
        if started:
            logger.info(f"ComfyUI started on port {used_port}.")
            return True, f"ComfyUI started on port {used_port}."
        logger.info(f"ComfyUI already running on port {used_port}.")
        return True, f"ComfyUI already running on port {used_port}."

    logger.error("Failed to start ComfyUI.")
    return False, "Failed to start ComfyUI."


def stop_comfy(port=8190):
    """Stop ComfyUI server if it was started by ContextUp."""
    service = ComfyUIService(port=port)
    ok, reason = service.stop(only_if_owned=True)
    if ok:
        logger.info("ComfyUI stopped.")
        return True, "ComfyUI stopped."
    if reason == "not_owned":
        return False, "ComfyUI not owned by ContextUp. Use Force Kill if needed."
    return False, "Failed to stop ComfyUI."


def open_comfy_console(port=8190):
    """Open a console window that tails ComfyUI logs."""
    service = ComfyUIService(port=port)
    ok, reason = service.open_console()
    if ok and reason == "already_open":
        return True, "ComfyUI console already open."
    if ok:
        return True, "ComfyUI console opened."
    return False, "Failed to open ComfyUI console."


def close_comfy_console(port=8190):
    """Close the ComfyUI log console window."""
    service = ComfyUIService(port=port)
    ok, reason = service.close_console()
    if ok:
        return True, "ComfyUI console closed."
    if reason == "not_running":
        return False, "ComfyUI console is not running."
    return False, "Failed to close ComfyUI console."


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "start":
            print(start_comfy()[1])
        elif cmd == "stop":
            print(stop_comfy()[1])
        elif cmd == "status":
            print("Running" if is_comfy_running() else "Stopped")
        elif cmd == "console":
            print(open_comfy_console()[1])
        elif cmd == "console-close":
            print(close_comfy_console()[1])
