"""
Clipboard Tools GUI.
Enhanced with better API key error handling and user guidance.
"""
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import threading
import os
from pathlib import Path

from core.paths import ROOT_DIR

def _get_root_cb():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.lift()
    return root

def _check_api_key():
    """Check if Gemini API key is configured."""
    # Check environment variable first
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return True, None
    
    # Check config file
    try:
        config_path = ROOT_DIR / "config" / "api_keys.json"
        if config_path.exists():
            import json
            with open(config_path, 'r') as f:
                keys = json.load(f)
                if keys.get("gemini_api_key") or keys.get("google_api_key"):
                    return True, None
    except:
        pass
    
    return False, (
        "Gemini API 키가 설정되지 않았습니다.\n\n"
        "설정 방법:\n"
        "1. Google AI Studio에서 API 키 발급:\n"
        "   https://aistudio.google.com/apikey\n\n"
        "2. 다음 중 하나의 방법으로 설정:\n"
        "   A) 환경 변수 설정:\n"
        "      GEMINI_API_KEY 또는 GOOGLE_API_KEY\n\n"
        "   B) config/api_keys.json 파일 생성:\n"
        '      {"gemini_api_key": "your-key-here"}'
    )

class ClipboardDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Clipboard Error Analysis")
        self.geometry("650x550")
        
        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 650) // 2
        y = (self.winfo_screenheight() - 550) // 2
        self.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        
        # Check API key first
        has_key, error_msg = _check_api_key()
        if not has_key:
            self.result_area.insert(tk.END, f"⚠️ API Key Error\n\n{error_msg}")
            self.retry_btn.configure(state=tk.DISABLED)
        else:
            self.start_analysis()
        
    def create_widgets(self):
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header_frame, text="AI Error Analysis", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="(Powered by Gemini)", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=10)
        
        # Result Area
        self.result_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, font=("Consolas", 10))
        self.result_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(self, padding="10")
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="Copy Result", command=self.copy_result).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        self.retry_btn = ttk.Button(btn_frame, text="Retry", command=self.start_analysis)
        self.retry_btn.pack(side=tk.LEFT)
        
    def start_analysis(self):
        self.result_area.delete(1.0, tk.END)
        self.result_area.insert(tk.END, "🔍 Analyzing clipboard content...\n\nPlease wait while the AI analyzes your error.\n")
        self.retry_btn.configure(state=tk.DISABLED)
        threading.Thread(target=self.run_analysis, daemon=True).start()
        
    def run_analysis(self):
        try:
            from utils.ai_runner import run_ai_script
            args = ["clipboard_error.py"]
            success, output = run_ai_script(*args)
            self.after(0, lambda: self.show_result(success, output))
        except Exception as e:
            self.after(0, lambda: self.show_result(False, str(e)))
        
    def show_result(self, success, output):
        self.retry_btn.configure(state=tk.NORMAL)
        self.result_area.delete(1.0, tk.END)
        
        if success:
            # Extract result
            if "--- Analysis Result ---" in output:
                output = output.split("--- Analysis Result ---")[1].strip()
            self.result_area.insert(tk.END, "✅ Analysis Complete\n\n")
            self.result_area.insert(tk.END, output)
        else:
            # Better error handling
            if "API key" in output.lower() or "api_key" in output.lower() or "authentication" in output.lower():
                _, api_error_msg = _check_api_key()
                if api_error_msg:
                    self.result_area.insert(tk.END, f"❌ API Error\n\n{api_error_msg}")
                else:
                    self.result_area.insert(tk.END, f"❌ API Error\n\n{output}")
            elif "rate limit" in output.lower() or "quota" in output.lower():
                self.result_area.insert(tk.END, "⏳ Rate Limit Exceeded\n\n")
                self.result_area.insert(tk.END, "API 요청 한도에 도달했습니다.\n")
                self.result_area.insert(tk.END, "잠시 후 다시 시도해주세요.\n\n")
                self.result_area.insert(tk.END, f"상세: {output[:500]}")
            elif "network" in output.lower() or "connection" in output.lower():
                self.result_area.insert(tk.END, "🌐 Network Error\n\n")
                self.result_area.insert(tk.END, "네트워크 연결을 확인해주세요.\n\n")
                self.result_area.insert(tk.END, f"상세: {output[:500]}")
            else:
                self.result_area.insert(tk.END, f"❌ Error\n\n{output}")

    def copy_result(self):
        text = self.result_area.get(1.0, tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Copied", "Result copied to clipboard!")

def analyze_error():
    """
    Open Clipboard Analysis dialog.
    """
    try:
        root = _get_root_cb()
        dialog = ClipboardDialog(root)
        root.wait_window(dialog)
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open clipboard tool: {e}")
