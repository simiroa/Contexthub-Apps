
import json
import urllib.request
import urllib.parse
try:
    import websocket # type: ignore
except ImportError:
    websocket = None
import uuid
import time
import subprocess
from pathlib import Path
import sys
import threading

class ComfyUIManager:
    """
    Manages Local ComfyUI Instance and API interactions.
    """
    # Common ports to check for existing ComfyUI servers
    COMMON_PORTS = [8190, 8188, 8189]
    
    def __init__(self, host="127.0.0.1", port=None, tools_dir=None):
        self.host = host
        self.preferred_port = port or 8190  # Default port for new server
        self.active_port = None  # Will be set when connection is established
        self.client_id = str(uuid.uuid4())
        self._we_started_server = False  # Track if we started the server
        self.launcher_path = None
        self.main_py_override = None
        
        # Load Settings for custom path
        from core.settings import load_settings
        settings = load_settings()
        custom_path = settings.get("COMFYUI_PATH", "").strip()
        self.use_launcher = bool(settings.get("COMFYUI_USE_LAUNCHER", False))
        
        if custom_path and Path(custom_path).exists():
             custom = Path(custom_path)
             if custom.is_file():
                 if custom.suffix.lower() in (".bat", ".cmd"):
                     if self.use_launcher:
                         self.launcher_path = custom
                 elif custom.suffix.lower() == ".py":
                     self.main_py_override = custom
                 base = custom.parent
                 if (base / "main.py").exists():
                     self.comfy_dir = base
                 elif (base / "ComfyUI" / "main.py").exists():
                     self.comfy_dir = base / "ComfyUI"
                 else:
                     self.comfy_dir = base
             else:
                 self.comfy_dir = custom
                 # Assume standard structure inside custom path, or check typical spots
                 # If user points to 'ComfyUI' folder
                 if (self.comfy_dir / "main.py").exists():
                     pass # Good
                 elif (self.comfy_dir / "ComfyUI" / "main.py").exists():
                     self.comfy_dir = self.comfy_dir / "ComfyUI"
                 
             # Try to find python
             # 1. Embedded
             self.python_exe = self.comfy_dir.parent / "python_embeded" / "python.exe"
             # 2. Venv
             if not self.python_exe.exists():
                 self.python_exe = self.comfy_dir / "venv" / "Scripts" / "python.exe"
             # 3. System (fallback later)
             
        elif tools_dir:
            self.comfy_dir = Path(tools_dir) / "ComfyUI" / "ComfyUI"
            self.python_exe = Path(tools_dir) / "ComfyUI" / "python_embeded" / "python.exe"
        else:
            # context_up_root = src/../.. = ContextUp
            base = Path(__file__).resolve().parents[3]
            self.comfy_dir = base / "tools" / "ComfyUI" / "ComfyUI"
            self.python_exe = base / "tools" / "ComfyUI" / "python_embeded" / "python.exe"

        if not self.python_exe.exists():
            print(f"[WARN] Embedded Python not found at {self.python_exe}, using system python.")
            self.python_exe = sys.executable
            
        self.process = None
        self._log_handle = None
        
        # Try to find existing server on startup
        self._detect_existing_server()

    def _detect_existing_server(self):
        """Check common ports for an already running ComfyUI server."""
        ports = [self.preferred_port] + [p for p in self.COMMON_PORTS if p != self.preferred_port]
        for port in ports:
            if self._check_port(port):
                self.active_port = port
                self._update_addresses()
                print(f"[OK] Found existing ComfyUI server on port {port}")
                return True
        return False

    def _check_port(self, port):
        """Check if ComfyUI is responding on a specific port."""
        try:
            url = f"http://{self.host}:{port}"
            # Localhost should be instant, reduce timeout to avoid blocking tray
            with urllib.request.urlopen(url, timeout=1.0) as response:
                return response.status == 200
        except:
            return False

    def _update_addresses(self):
        """Update WebSocket and HTTP addresses based on active port."""
        if self.active_port:
            self.ws_address = f"ws://{self.host}:{self.active_port}/ws?clientId={{}}"
            self.server_address = f"http://{self.host}:{self.active_port}"
        else:
            self.ws_address = f"ws://{self.host}:{self.preferred_port}/ws?clientId={{}}"
            self.server_address = f"http://{self.host}:{self.preferred_port}"

    @property
    def port(self):
        """Return the currently active port."""
        return self.active_port or self.preferred_port

    def set_active_port(self, port):
        """Force active port and update internal addresses."""
        self.active_port = port
        self._update_addresses()

    def is_running(self):
        """Check if ComfyUI is responding on any known port."""
        # First check active port if set
        if self.active_port and self._check_port(self.active_port):
            return True
        # Otherwise scan all ports
        return self._detect_existing_server()

    def start(self, log_file=None, creationflags=None):
        """Start ComfyUI server if not running."""
        if self.is_running():
            print(f"[OK] ComfyUI is already running on port {self.active_port}.")
            return True
            
        main_py = self.main_py_override or (self.comfy_dir / "main.py")
        if not main_py.exists():
            print(f"[ERROR] ComfyUI not found at {main_py}")
            if self._log_handle:
                try:
                    self._log_handle.write(f"[ERROR] ComfyUI not found at {main_py}\n")
                    self._log_handle.flush()
                except Exception:
                    pass
            return False
            
        print(f"[INFO] Starting ComfyUI from {self.comfy_dir} on port {self.preferred_port}...")
        
        # Build command with GPU options from settings
        from core.settings import load_settings
        settings = load_settings()
        
        cmd = [str(self.python_exe), "-s", str(main_py), 
               "--listen", self.host, 
               "--port", str(self.preferred_port)]
        
        # Add GPU optimization flags based on settings
        gpu_options = settings.get("COMFYUI_GPU_OPTIONS", {})
        
        # Windows standalone build (recommended for embedded python)
        if gpu_options.get("windows_standalone", True):
            cmd.append("--windows-standalone-build")
        
        # SAGE Attention (faster inference on newer GPUs)
        if gpu_options.get("sage_attention", False):
            cmd.append("--use-sage-attention")
        
        # FP16 Fast Accumulation (faster but less precision)
        if gpu_options.get("fp16_fast_accumulation", False):
            cmd.append("--fast")
        
        # Low VRAM mode
        if gpu_options.get("low_vram", False):
            cmd.append("--lowvram")
        
        # CPU only mode
        if gpu_options.get("cpu_only", False):
            cmd.append("--cpu")
        
        print(f"Command: {' '.join(cmd)}")

        if creationflags is None:
            creationflags = 0x08000000  # CREATE_NO_WINDOW

        stdout_target = None
        stderr_target = None
        if log_file:
            try:
                log_path = Path(log_file)
                log_path.parent.mkdir(exist_ok=True, parents=True)
                self._log_handle = open(log_path, "a", encoding="utf-8")
                stdout_target = self._log_handle
                stderr_target = self._log_handle
            except Exception as exc:
                print(f"[WARN] Failed to open ComfyUI log file: {exc}")

        if self.launcher_path:
            try:
                launcher_cmd = ["cmd", "/c", str(self.launcher_path)]
                print(f"Command: {' '.join(launcher_cmd)}")
                self.process = subprocess.Popen(
                    launcher_cmd,
                    cwd=str(self.launcher_path.parent),
                    creationflags=creationflags,
                    stdout=stdout_target,
                    stderr=stderr_target,
                )

                for _ in range(60):
                    time.sleep(1)
                    if self._detect_existing_server():
                        self._we_started_server = True
                        self.process = None
                        print("[OK] ComfyUI Started!")
                        return True

                print("[ERROR] Failed to start ComfyUI (timeout).")
                if self._log_handle:
                    try:
                        self._log_handle.close()
                    except Exception:
                        pass
                    self._log_handle = None
                return False
            except Exception as exc:
                print(f"[ERROR] ComfyUI launcher failed: {exc}")
                if self._log_handle:
                    try:
                        self._log_handle.write(f"[ERROR] Launcher failed: {exc}\n")
                        self._log_handle.flush()
                    except Exception:
                        pass
                return False

        self.process = subprocess.Popen(
            cmd,
            cwd=str(self.comfy_dir),
            creationflags=creationflags,
            stdout=stdout_target,
            stderr=stderr_target,
        )
        
        # Wait for valid response
        for _ in range(60):
            time.sleep(1)
            if self._check_port(self.preferred_port):
                self.active_port = self.preferred_port
                self._update_addresses()
                self._we_started_server = True
                print("[OK] ComfyUI Started!")
                return True
        
        print("[ERROR] Failed to start ComfyUI (timeout).")
        if self._log_handle:
            try:
                self._log_handle.close()
            except Exception:
                pass
            self._log_handle = None
        return False

    def queue_prompt(self, prompt_workflow):
        p = {"prompt": prompt_workflow, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"{self.server_address}/prompt", data=data)
        try:
            return json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            print(f"[ERROR] HTTP Error {e.code}: {e.read().decode('utf-8')}")
            raise e

    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"{self.server_address}/view?{url_values}") as response:
            return response.read()

    def get_history(self, prompt_id):
        with urllib.request.urlopen(f"{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())

    def generate_image(self, workflow, output_node_id=None, progress_callback=None):
        """
        Execute workflow and return images.
        progress_callback: function(value, max_value)
        """
        if not self.is_running():
            if not self.start():
                raise Exception("ComfyUI is not available.")

        ws = websocket.WebSocket()
        ws.connect(self.ws_address.format(self.client_id))
        
        prompt_res = self.queue_prompt(workflow)
        prompt_id = prompt_res['prompt_id']
        
        output_images = {}
        
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                # print(message) # Debug
                if message['type'] == 'progress':
                    data = message['data']
                    if progress_callback:
                        progress_callback(data['value'], data['max'])
                        
                elif message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break # Execution done
                elif message['type'] == 'execution_error':
                    print(f"[ERROR] ComfyUI Error: {message['data']}")
                    return []
            else:
                continue # Binary data (previews)

        # Get history to find outputs
        history = self.get_history(prompt_id)[prompt_id]
        outputs = history['outputs']
        
        images_data = []
        
        for node_id in outputs:
            # If specifically looking for one node, filter here
            if output_node_id and str(node_id) != str(output_node_id):
                continue
                
            node_output = outputs[node_id]
            if 'images' in node_output:
                for image in node_output['images']:
                    img_data = self.get_image(image['filename'], image['subfolder'], image['type'])
                    images_data.append(img_data)
        
        ws.close()
        return images_data

    def unload_models(self):
        """Free VRAM by unloading models."""
        try:
            # ComfyUI doesn't have a standard API for this, but we can try to free memory
            # or just restart/kill.
            # Some custom nodes expose this, but standard doesn't.
            # Best way to ensure GPU release is to kill the server process if we spawned it.
            pass
        except:
            pass

    def stop(self):
        """Stop ComfyUI server."""
        if self.process and not self.launcher_path:
            print("[INFO] Stopping ComfyUI...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            print("[OK] ComfyUI Stopped.")
            if self._log_handle:
                try:
                    self._log_handle.close()
                except Exception:
                    pass
                self._log_handle = None
        elif self.active_port or self.preferred_port:
            # Try to kill by port if we don't have process handle
            port_to_kill = self.active_port or self.preferred_port
            print(f"[INFO] Killing ComfyUI on port {port_to_kill}...")
            self.kill_by_port(port_to_kill)
            if self._log_handle:
                try:
                    self._log_handle.close()
                except Exception:
                    pass
                self._log_handle = None

    @staticmethod
    def kill_by_port(port):
        """Kill process listening on a specific port (Windows only)."""
        try:
            # Find PID
            cmd = f"netstat -ano | findstr :{port}"
            output = subprocess.check_output(cmd, shell=True).decode()
            
            # Parse PIDs
            pids = set()
            for line in output.splitlines():
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[-1]
                    # Ensure it's listening
                    if "LISTENING" in line:
                        pids.add(pid)
            
            # Kill PIDs
            for pid in pids:
                subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                print(f"[OK] Killed process {pid} on port {port}")
                
        except Exception as e:
            print(f"[WARN] Failed to kill by port {port}: {e}")

    @classmethod
    def kill_all_instances(cls):
        """Force kill all ComfyUI python processes."""
        import logging
        logger = logging.getLogger("ComfyUIManager")
        logger.info("Cleaning up all ComfyUI instances...")
        
        # 1. Kill by common ports first
        killed_any = False
        for port in cls.COMMON_PORTS:
            # We can't strictly know if we killed one, but we try
            cls.kill_by_port(port)

        # 2. Aggressive search by Command Line (WMIC)
        # Finds python processes running 'ComfyUI\main.py' or 'ComfyUI/main.py'
        try:
            cmd = "wmic process where \"name='python.exe' and CommandLine like '%ComfyUI%main.py%'\" get ProcessId"
            output = subprocess.check_output(cmd, shell=True).decode()
            
            pids = [line.strip() for line in output.splitlines() if line.strip().isdigit()]
            
            if pids:
                logger.info(f"found {len(pids)} lingering ComfyUI processes via WMIC.")
                for pid in pids:
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                    logger.info(f"Killed lingering process {pid}")
                    killed_any = True
        except Exception as e:
            logger.error(f"WMIC cleanup failed: {e}")
            
        return True

    def get_input_options(self, node_name, input_name):
        """
        Fetch available options for a node's input (e.g., checkpoint names).
        Returns list of strings or [].
        """
        try:
            url = f"{self.server_address}/object_info/{node_name}"
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read())
                
            # object_info returns { "NodeName": { "input": { "required": { "params": [type, {config}] } } } }
            # But specific structure varies.
            # Usually: data[node_name]['input']['required'][input_name][0] is the list if it's a dropdown.
            
            node_info = data.get(node_name, {})
            inputs = node_info.get("input", {}).get("required", {})
            
            # Check required inputs
            target_input = inputs.get(input_name)
            if not target_input:
                # Check optional
                inputs = node_info.get("input", {}).get("optional", {})
                target_input = inputs.get(input_name)
                
            if target_input and isinstance(target_input[0], list):
                return target_input[0]
                
            return []
        except Exception as e:
            print(f"[WARN] Failed to fetch options for {node_name}.{input_name}: {e}")
            return []

def get_z_image_workflow(prompt, seed, steps=8, width=512, height=512):
    # This is a dummy example. A real Z-Image workflow is needed.
    # We will use a standard SDXL Turbo workflow for now as placeholder.
    # Replace this structure with the actual specific workflow.
    return {} 
 
