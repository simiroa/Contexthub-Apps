from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable

try:
    import websocket  # type: ignore
except ImportError:
    websocket = None


COMMON_PORTS = (8190, 8188, 8189)
HOST = "127.0.0.1"


def _check_port(port: int, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}", timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def detect_server_port() -> int | None:
    for port in COMMON_PORTS:
        if _check_port(port):
            return port
    return None


def is_server_alive() -> bool:
    return detect_server_port() is not None


def _server_address(port: int) -> str:
    return f"http://{HOST}:{port}"


def upload_image(port: int, image_path: Path) -> str:
    """Upload an image file to ComfyUI's /upload/image and return server-side name."""
    boundary = uuid.uuid4().hex
    with image_path.open("rb") as fp:
        file_bytes = fp.read()
    filename = image_path.name
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    body += file_bytes
    body += f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{_server_address(port)}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req) as response:
        payload = json.loads(response.read())
    return payload.get("name") or filename


def queue_prompt(port: int, workflow: dict[str, Any], client_id: str) -> str:
    data = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(f"{_server_address(port)}/prompt", data=data)
    try:
        result = json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ComfyUI rejected workflow ({exc.code}): {detail}") from exc
    return result["prompt_id"]


def get_history(port: int, prompt_id: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{_server_address(port)}/history/{prompt_id}") as response:
        return json.loads(response.read())


def get_image_bytes(port: int, filename: str, subfolder: str, folder_type: str) -> bytes:
    params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
    with urllib.request.urlopen(f"{_server_address(port)}/view?{params}") as response:
        return response.read()


def run_workflow(
    workflow: dict[str, Any],
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[tuple[str, bytes]]:
    """Submit workflow, block until done, return [(filename, image_bytes), ...]."""
    port = detect_server_port()
    if port is None:
        raise RuntimeError("ComfyUI server not reachable. Start it via the ComfyUI Dashboard app.")
    if websocket is None:
        raise RuntimeError("Python package 'websocket-client' is required.")

    client_id = str(uuid.uuid4())
    ws = websocket.WebSocket()
    ws.connect(f"ws://{HOST}:{port}/ws?clientId={client_id}")
    try:
        prompt_id = queue_prompt(port, workflow, client_id)
        while True:
            raw = ws.recv()
            if not isinstance(raw, str):
                continue
            message = json.loads(raw)
            mtype = message.get("type")
            data = message.get("data", {})
            if mtype == "progress" and progress_callback:
                progress_callback(int(data.get("value", 0)), int(data.get("max", 1)))
            elif mtype == "executing" and data.get("prompt_id") == prompt_id and data.get("node") is None:
                break
            elif mtype == "execution_error":
                raise RuntimeError(f"ComfyUI execution error: {data}")
    finally:
        ws.close()

    history = get_history(port, prompt_id).get(prompt_id, {})
    outputs = history.get("outputs", {})
    results: list[tuple[str, bytes]] = []
    for node_output in outputs.values():
        for image in node_output.get("images", []) or []:
            try:
                payload = get_image_bytes(port, image["filename"], image.get("subfolder", ""), image.get("type", "output"))
            except Exception as exc:
                print(f"[ai_upscaler] failed to fetch image {image}: {exc}", file=sys.stderr)
                continue
            results.append((image["filename"], payload))
    return results
