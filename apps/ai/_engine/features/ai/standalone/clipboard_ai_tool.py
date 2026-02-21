"""
Unified Clipboard AI Analysis Tool (Gemini 2.5)
Analyzes clipboard content (Image or Text) for errors, descriptions, or summaries.
Features: Always-on-Top, Auto-Monitor, Duplicate Prevention.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from utils.i18n import t
from PIL import ImageGrab, Image, ImageTk
import pyperclip
import threading
import sys
import os
import time
import hashlib
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent.parent
sys.path.append(str(src_dir))

from utils.gui_lib import BaseWindow, THEME_BTN_PRIMARY, THEME_BTN_HOVER
from core.settings import load_settings

# Try to import google.genai
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

def get_gemini_client():
    if genai is None:
        return None
    settings = load_settings()
    api_key = settings.get('GEMINI_API_KEY')
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

class ClipboardAIGUI(BaseWindow):
    def __init__(self):
        super().__init__(title="ContextUp Clipboard AI (Gemini)", width=600, height=700, icon_name="ai_clipboard_gemini")
        
        # Always on Top
        self.attributes('-topmost', True)
        
        self.last_content_hash = None
        self.current_content = None
        self.content_type = None
        self.is_monitoring = True
        
        self.create_widgets()
        self.monitor_clipboard()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_widgets(self):
        # 1. Header & Settings
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(header_frame, text="Clipboard Analysis", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        
        self.var_top = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(header_frame, text="Always on Top", variable=self.var_top, command=self.toggle_top, width=100).pack(side="right")
        
        # 2. Preview Area
        self.preview_frame = ctk.CTkFrame(self.main_frame, height=200)
        self.preview_frame.pack(fill="x", padx=10, pady=5)
        self.preview_frame.pack_propagate(False) # Fixed height
        
        self.lbl_status = ctk.CTkLabel(self.preview_frame, text="Waiting for clipboard content...", text_color="gray")
        self.lbl_status.place(relx=0.5, rely=0.5, anchor="center")
        
        self.lbl_image_preview = ctk.CTkLabel(self.preview_frame, text="")
        self.lbl_image_preview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 3. Action Bar
        action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=10)
        
        self.btn_analyze = ctk.CTkButton(action_frame, text="Analyze with Gemini", command=self.start_analysis, 
                                       font=ctk.CTkFont(size=14, weight="bold"), height=40, 
                                       fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER)
        self.btn_analyze.pack(fill="x")
        
        # Auto-Analyze Option
        self.var_auto = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(self.main_frame, text="Auto-Analyze New Content (Use with caution)", variable=self.var_auto).pack(pady=5)

        # 4. Result Area
        ctk.CTkLabel(self.main_frame, text="Analysis Result:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.result_area = ctk.CTkTextbox(self.main_frame, font=("Consolas", 11))
        self.result_area.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 5. Footer
        footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        footer_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(footer_frame, text="Clear", command=self.clear_all, fg_color="gray", width=80).pack(side="left")
        ctk.CTkButton(footer_frame, text="Copy Result", command=self.copy_result, width=120).pack(side="right")

    def toggle_top(self):
        self.attributes('-topmost', self.var_top.get())

    def monitor_clipboard(self):
        if not self.winfo_exists(): return
        
        try:
            # Check Image
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                # Calculate hash to detect changes (simple size+mode check first, then bytes if needed)
                # For performance, we'll use a simple signature
                img_hash = f"IMG_{img.size}_{img.mode}"
                # To be more robust, we could sample pixels, but let's trust size/mode + timestamp if needed
                # Actually, user might copy same image again.
                # Let's use a small buffer hash
                img_small = img.resize((10, 10))
                img_hash = f"IMG_{hash(img_small.tobytes())}"
                
                if img_hash != self.last_content_hash:
                    self.last_content_hash = img_hash
                    self.content_type = "image"
                    self.current_content = img
                    self.update_preview_image(img)
                    if self.var_auto.get():
                        self.start_analysis()
            
            else:
                # Check Text
                text = pyperclip.paste()
                if text and len(text.strip()) > 0:
                    text_hash = f"TXT_{hash(text)}"
                    if text_hash != self.last_content_hash:
                        self.last_content_hash = text_hash
                        self.content_type = "text"
                        self.current_content = text
                        self.update_preview_text(text)
                        if self.var_auto.get():
                            self.start_analysis()
                            
        except Exception as e:
            print(f"Monitor error: {e}")
            
        self.after(1000, self.monitor_clipboard)

    def update_preview_image(self, img):
        self.lbl_status.place_forget()
        
        # Resize for preview
        w, h = img.size
        aspect = w / h
        target_h = 190
        target_w = int(target_h * aspect)
        
        if target_w > 500:
            target_w = 500
            target_h = int(target_w / aspect)
            
        preview_img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        self.tk_img = ctk.CTkImage(light_image=preview_img, dark_image=preview_img, size=(target_w, target_h))
        
        self.lbl_image_preview.configure(image=self.tk_img, text="")
        self.btn_analyze.configure(text=f"Analyze Image ({w}x{h})", state="normal")

    def update_preview_text(self, text):
        self.lbl_status.place_forget()
        self.lbl_image_preview.configure(image=None, text=text[:500])
        self.btn_analyze.configure(text="Analyze Text", state="normal")

    def start_analysis(self):
        if not self.current_content: return
        
        self.btn_analyze.configure(state="disabled", text="Analyzing...")
        self.result_area.delete("1.0", "end")
        self.result_area.insert("end", "Sending to Gemini 2.5...\n")
        
        threading.Thread(target=self.run_gemini, daemon=True).start()

    def run_gemini(self):
        client = get_gemini_client()
        if not client:
            self.update_result("Error: Gemini API Key not found.")
            return

        try:
            model_name = "gemini-2.0-flash-exp" 
            
            if self.content_type == "image":
                prompt = (
                    "Analyze this image. "
                    "1. If it contains an error message, stack trace, or code issue: Explain the error clearly, why it happened, and provide a solution or fix. "
                    "2. If it is a general image: Describe what is in the image in detail. "
                    "3. If it is text/screenshot: Extract the text and summarize it."
                )
                contents = [prompt, self.current_content]
            else:
                prompt = (
                    "Analyze the following text. "
                    "1. If it is an error log or code: Explain the bug and provide a corrected version or fix. "
                    "2. If it is general text: Summarize it and extract key points."
                    "\n\nText Content:\n"
                )
                contents = [prompt + self.current_content]
                
            response = client.models.generate_content(
                model=model_name,
                contents=contents
            )
            
            if response.text:
                self.update_result(response.text)
            else:
                self.update_result("No text response received.")
                
        except Exception as e:
            self.update_result(f"Error: {e}")

    def update_result(self, text):
        self.after(0, lambda: self._update_ui(text))
        
    def _update_ui(self, text):
        self.result_area.delete("1.0", "end")
        self.result_area.insert("end", text)
        self.btn_analyze.configure(state="normal", text="Analyze Again")

    def clear_all(self):
        self.result_area.delete("1.0", "end")
        self.lbl_image_preview.configure(image=None, text="")
        self.lbl_status.place(relx=0.5, rely=0.5, anchor="center")
        self.current_content = None
        self.last_content_hash = None
        self.btn_analyze.configure(text="Analyze with Gemini", state="disabled")

    def copy_result(self):
        text = self.result_area.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo(t("common.success"), "Result copied to clipboard.")

    def on_closing(self):
        self.is_monitoring = False
        self.destroy()

if __name__ == "__main__":
    app = ClipboardAIGUI()
    app.mainloop()
