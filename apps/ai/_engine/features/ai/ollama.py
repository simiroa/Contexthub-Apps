"""
Ollama Vision GUI Tools.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from utils.i18n import t
from pathlib import Path
import threading
import sys

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/ai -> src
sys.path.append(str(src_dir))

from utils.ai_runner import run_ai_script
from utils.gui_lib import BaseWindow

class OllamaVisionGUI(BaseWindow):
    def __init__(self, target_path=None):
        super().__init__(title="ContextUp Ollama Vision", width=600, height=500, icon_name="image_analyze_ollama")
        self.image_path = target_path
        
        self.create_widgets()
        self.load_models()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_widgets(self):
        # Header
        src_text = f"Source: {Path(self.image_path).name}" if self.image_path else "Source: Clipboard"
        self.add_header(src_text)
        
        # Top frame
        top_frame = ctk.CTkFrame(self.main_frame)
        top_frame.pack(fill="x", padx=20, pady=10)
        
        # Model Selection
        ctk.CTkLabel(top_frame, text="Model:").pack(side="left", padx=(20, 5), pady=10)
        self.model_var = ctk.StringVar(value="llava")
        self.model_combo = ctk.CTkComboBox(top_frame, variable=self.model_var, values=["llava"], width=150)
        self.model_combo.pack(side="left", padx=5)
        
        # Type Selection
        ctk.CTkLabel(top_frame, text="Type:").pack(side="left", padx=(20, 5), pady=10)
        self.type_var = ctk.StringVar(value="describe")
        types = ["describe", "analyze", "extract_text", "detect_objects"]
        self.type_combo = ctk.CTkComboBox(top_frame, variable=self.type_var, values=types, width=150)
        self.type_combo.pack(side="left", padx=5)
        
        # Analyze Button
        self.btn_analyze = ctk.CTkButton(top_frame, text="Analyze", command=self.start_analysis)
        self.btn_analyze.pack(side="right", padx=20)
        
        # Result Area
        ctk.CTkLabel(self.main_frame, text="Result:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 5))
        
        self.result_area = ctk.CTkTextbox(self.main_frame, font=("Consolas", 10))
        self.result_area.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Bottom frame: Actions
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(btn_frame, text="Copy to Clipboard", command=self.copy_result).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Close", fg_color="transparent", border_width=1, border_color="gray", command=self.destroy).pack(side="right", padx=5)
        
    def load_models(self):
        """Load available models in background."""
        def _load():
            success, output = run_ai_script("ollama_vision.py", "--list-models")
            if success:
                models = []
                for line in output.splitlines():
                    if line.strip().startswith("-"):
                        models.append(line.strip("- ").strip())
                
                if models:
                    self.model_combo.configure(values=models)
                    if "llava" in models:
                        self.model_combo.set("llava")
                    else:
                        self.model_combo.set(models[0])
            else:
                self.result_area.insert("end", "Error: Could not list models. Is Ollama running?\n")
                
        threading.Thread(target=_load, daemon=True).start()
        
    def start_analysis(self):
        self.btn_analyze.configure(state="disabled", text="Analyzing...")
        self.result_area.delete("1.0", "end")
        self.result_area.insert("end", "Analyzing... Please wait.\n")
        
        threading.Thread(target=self.run_analysis, daemon=True).start()
        
    def run_analysis(self):
        args = ["ollama_vision.py"]
        
        if self.image_path:
            args.append(str(self.image_path))
        else:
            args.append("--clipboard")
            
        args.extend(["--model", self.model_var.get()])
        args.extend(["--type", self.type_var.get()])
        
        success, output = run_ai_script(*args)
        
        self.after(0, lambda: self.show_result(success, output))
        
    def show_result(self, success, output):
        self.btn_analyze.configure(state="normal", text="Analyze")
        self.result_area.delete("1.0", "end")
        
        if success:
            # Extract result between markers if present
            if "--- Result ---" in output:
                parts = output.split("--- Result ---")
                if len(parts) > 1:
                    result = parts[1].split("--------------")[0].strip()
                    self.result_area.insert("end", result)
                    return
            
            self.result_area.insert("end", output)
        else:
            self.result_area.insert("end", f"Error:\n{output}")

    def copy_result(self):
        text = self.result_area.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo(t("common.success"), "Result copied to clipboard!")

    def on_closing(self):
        self.destroy()

def analyze_image(target_path: str = None):
    """
    Open Ollama Vision dialog.
    If target_path is None, uses clipboard.
    """
    try:
        if target_path:
            # Check if it's an image
            img_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
            if Path(target_path).suffix.lower() not in img_exts:
                messagebox.showinfo(t("common.info"), "Selected file is not an image.")
                return
        
        app = OllamaVisionGUI(target_path)
        app.mainloop()
            
    except Exception as e:
        messagebox.showerror(t("common.error"), f"Failed to open vision tool: {e}")

def analyze_clipboard():
    """Analyze image from clipboard."""
    analyze_image(None)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_image(sys.argv[1])
    else:
        analyze_clipboard()
