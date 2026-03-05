"""
Tool: AI Text Lab (AI 텍스트 연구소)
Features: Unified text hub for AI refinement (Ollama, Gemini) and Machine Translation (Google).
Supports streaming for LLMs, Auto-Clip, Pin, and Opacity control.
"""
import os
import sys
import threading
import time
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
import traceback

# Add src to path
try:
    current_dir = Path(__file__).resolve().parent
    src_dir = current_dir.parent.parent  # features/utilities -> src
    sys.path.append(str(src_dir))
except: pass

from utils.gui_lib import BaseWindow, THEME_BG, THEME_CARD, THEME_BORDER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, THEME_TEXT_MAIN, THEME_ACCENT
from core.logger import setup_logger
from core.settings import load_settings
from utils.i18n import t

logger = setup_logger("tool_ai_text_lab")

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        try:
            x, y, _, _ = self.widget.bbox("insert")
        except:
            x, y = 0, 0
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, background="SystemButtonFace", foreground="SystemWindowText", 
                        relief="solid", borderwidth=1, font=("Arial", 9))
        label.pack()

    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class AITextLabApp(BaseWindow):
    # Presets with think mode configuration
    # Format: {name: (prompt, use_think, target_lang_if_mt)}
    PRESETS = {
        "-- Editing --": (None, False, None),
        "🔍 Grammar Fix": ("Correct the grammar of the following text. Fix grammatical errors, typos, and punctuation. Maintain the original tone and style. Output ONLY the corrected text.", False, None),
        "📝 Summarize": ("Summarize the following text into concise bullet points. Extract key information, be brief. Output ONLY the summary.", False, None),
        "🔖 핵심 요약 (한문단)": ("Summarize the key points of the following text into a natural, fluent single paragraph in Korean. Output ONLY the summary.", False, "ko"),
        "📋 3줄 요약 (한글)": ("Summarize the following text into exactly 3 concise bullet points in Korean. Output ONLY the summary.", False, "ko"),
        "📜 10줄 요약 (한글)": ("Summarize the following text into exactly 10 concise bullet points in Korean. Output ONLY the summary.", False, "ko"),
        "📧 Professional Email": ("Rewrite the following text as a professional email. Formal, polite, concise, structured for business. Output ONLY the rewritten text.", False, None),
        
        "-- Creative --": (None, False, None),
        "🎨 Midjourney Prompt": ("Rewrite the following text as a high-quality Midjourney prompt. Enhance visual descriptions, add lighting/style keywords (e.g., cinematic lighting, 8k, hyperrealistic), remove conversational filler. Comma separated. Output ONLY the prompt.", True, None),
        "🎥 Video Generation": ("Rewrite the following text as a high-quality video generation prompt (Veo3/Sora/Gen3 style). Describe camera movement (pan, zoom), lighting, motion, and cinematic composition. Output ONLY the prompt.", True, None),
        "🖋️ Flash Fiction": ("Write a very short, creative story (flash fiction) based on the input text. Be imaginative and engaging. Output ONLY the story.", False, None),
        "📱 SNS Post": ("Rewrite the following text as an engaging SNS post (Instagram/X style). Use appropriate hashtags and emojis. Catchy and trendy. Output ONLY the post.", False, None),
        
        "-- Logic --": (None, False, None),
        "🤖 Agent Order": ("Transform the following planning document or ideas into a highly structured 'Agent Order' (System Instruction). Organize it with clear sections: Role, Context, Objective, Constraints, and Step-by-Step Instructions. Use professional and precise language suitable for an AI agent. Output ONLY the structured instruction.", True, None),
        "🧪 Code Explainer": ("Explain the following code snippet concisely but thoroughly. Break down how it works and its purpose. Output ONLY the explanation.", False, None),
        "🧠 Concept Simplifier": ("Explain the following text or concept in extremely simple terms, as if explaining to a five-year-old (ELI5). Use simple analogies. Output ONLY the explanation.", False, None),
        "📄 Marketing Copy": ("Transform the following text into persuasive marketing or ad copy. Focus on benefits and call to action. Compelling and professional. Output ONLY the copy.", False, None),
        
        "-- Translation --": (None, False, None),
        "🇰🇷 Translate to Korean": ("Translate the following text to natural, fluent Korean. Native-level phrasing. Output ONLY the translation.", False, "ko"),
        "🇺🇸 Translate to English": ("Translate the following text to natural, fluent English. Native-level phrasing. Output ONLY the translation.", False, "en"),
        "🇫🇷 Translate to French": ("Translate the following text to natural, fluent French. Native-level phrasing. Output ONLY the translation.", False, "fr"),
        "🇯🇵 Translate to Japanese": ("Translate the following text to natural, fluent Japanese. Native-level phrasing. Output ONLY the translation.", False, "ja"),
    }
    
    MACHINE_TRANSLATION = "🌐 Machine Translation (Google)"
    
    # Available LLM models
    OLLAMA_MODELS = ["qwen3:8b", "qwen3:4b", "qwen3:1.7b", "llama3.2:3b", "gemma3:4b", "phi4:14b"]
    GEMINI_MODELS = ["✦ gemini-2.5-flash", "✦ gemini-2.0-flash"]

    def __init__(self):
        super().__init__(title="AI Text Lab", width=480, height=650, icon_name="ai_text_lab")
        self.minsize(420, 450)
        self.resizable(True, True)
        
        # Borderless & Custom Title Bar Prep
        self.overrideredirect(True)
        self._offsetx = 0
        self._offsety = 0
        
        # State
        self.debounce_timer = None
        self.is_pinned = False
        self.is_auto_clip = False
        self.opacity_slider_visible = False
        self.current_preset = "🔍 Grammar Fix"
        self.last_input_text = ""
        self.last_preset = ""
        self.request_counter = 0
        self.ollama_ready = False
        self.current_model = "qwen3:8b"
        self.force_think = None
        self.is_streaming = False
        self.cancel_stream = False
        self.gemini_cooldown_until = 0
        self.last_clipboard_text = ""
        self.is_processing = False  # Locking mechanism
        self.MAX_CHARS = 10000       # Safety limit
        
        self.translator = None
        self.settings = load_settings()
        self.gemini_api_key = self.settings.get("GEMINI_API_KEY", "")
        self.gemini_client = None
        
        # UI Setup
        self.setup_modern_ui()
        
        # Async Init
        self.status_label.configure(text="연결 초기화 중...")
        threading.Thread(target=self.init_backends, daemon=True).start()
        
        self.start_clipboard_poll()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_modern_ui(self):
        """Redesign with custom title bar and unified panel look"""
        # 1. Clean up BaseWindow defaults if they exist to avoid geometry conflicts
        if hasattr(self, 'main_frame'):
            self.main_frame.pack_forget()
        if hasattr(self, 'title_bar'):
            self.title_bar.pack_forget()
            
        # 2. Appearance & Background (Reusing BaseWindow.outer_frame)
        TRANS_KEY_LOCAL = "#000001"
        self.configure(fg_color=TRANS_KEY_LOCAL)
        self.wm_attributes("-transparentcolor", TRANS_KEY_LOCAL)
        
        # Main Window Appearance
        BG_COLOR = "#050505"         # Deepest black
        HEADER_BG = "#111111"        # Slightly lighter for contrast
        SECTION_BG = "#0A0A0A"       # Editor Background
        ACCENT_ORANGE = "#E67E22"
        ACCENT_PURPLE = "#9B59B6"
        
        # Use existing outer_frame from BaseWindow instead of creating new one
        self.outer_frame.configure(fg_color=THEME_BG, corner_radius=16, border_width=1, border_color=THEME_BORDER)
        
        # === 2. TITLE BAR ===
        self.title_bar = ctk.CTkFrame(self.outer_frame, fg_color="transparent", height=40, corner_radius=0)
        self.title_bar.pack(fill="x", side="top", padx=10, pady=(4, 0))
        
        # Title
        self.title_label = ctk.CTkLabel(self.title_bar, text=" ✨ AI RED", font=("Segoe UI", 13, "bold"), text_color="#E0E0E0")
        self.title_label.pack(side="left", padx=(4, 0))
        ctk.CTkLabel(self.title_bar, text=" | Lab", font=("Segoe UI", 13), text_color="#666").pack(side="left")
        
        # Window Controls
        ctrl_frame = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        ctrl_frame.pack(side="right")
        
        self.btn_min = ctk.CTkButton(ctrl_frame, text="─", width=32, height=28, fg_color="transparent", hover_color="#222", command=self.minimize_window, font=("Arial", 11), corner_radius=6)
        self.btn_min.pack(side="left", padx=2)
        
        self.btn_close = ctk.CTkButton(ctrl_frame, text="✕", width=32, height=28, fg_color="transparent", hover_color="#922B21", command=self.on_closing, font=("Arial", 11), corner_radius=6)
        self.btn_close.pack(side="left", padx=2)

        # Drag setup
        for w in [self.title_bar, self.title_label, ctrl_frame]:
            w.bind("<Button-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)

        # === 3. HEADER AREA ===
        self.header_frame = ctk.CTkFrame(self.outer_frame, fg_color=THEME_CARD, corner_radius=12, border_width=1, border_color=THEME_BORDER)
        self.header_frame.pack(fill="x", padx=14, pady=10)
        
        # Row 0: Top Status & Indicators
        top_row = ctk.CTkFrame(self.header_frame, fg_color="transparent", height=20)
        top_row.pack(fill="x", padx=14, pady=(8, 2))
        
        self.status_label = ctk.CTkLabel(top_row, text="Ready", text_color="#555", font=("Segoe UI", 10, "bold"), anchor="w")
        self.status_label.pack(side="left")
        
        # Row 1: Primary Controls (Grid)
        grid_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        grid_box.pack(fill="x", padx=10, pady=(2, 10))
        grid_box.grid_columnconfigure(0, weight=1) 
        grid_box.grid_columnconfigure(1, weight=0) 
        
        # Preset Menu (Left)
        self.preset_var = ctk.StringVar(value=self.current_preset)
        self.opt_preset = ctk.CTkOptionMenu(
            grid_box, variable=self.preset_var, height=40,
            values=list(self.PRESETS.keys()),
            command=self.on_preset_change, font=("Segoe UI", 13, "bold"),
            fg_color=THEME_DROPDOWN_BTN, 
            button_color=THEME_DROPDOWN_BTN, 
            button_hover_color=THEME_DROPDOWN_HOVER,
            dropdown_fg_color=THEME_BG, 
            dropdown_hover_color=THEME_DROPDOWN_HOVER,
            dropdown_text_color=THEME_TEXT_MAIN,
            dropdown_font=("Segoe UI", 12),
            corner_radius=10, anchor="w"
        )
        self.opt_preset.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        
        # RUN Button (Right) - Big & Bold
        self.btn_check = ctk.CTkButton(
            grid_box, text="RUN PROCESS", command=self.trigger_check_manual, 
            height=40, width=110,
            fg_color=ACCENT_ORANGE, hover_color="#D35400", 
            font=("Segoe UI", 12, "bold"), text_color="white",
            corner_radius=8
        )
        self.btn_check.grid(row=0, column=1)

        # Row 2: Secondary Settings (Model, etc.)
        settings_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        settings_row.pack(fill="x", padx=10, pady=(0, 10))
        
        # Model Selector
        ctk.CTkLabel(settings_row, text="Model", font=("", 10, "bold"), text_color="#444").pack(side="left", padx=(4, 6))
        
        self.model_var = ctk.StringVar(value=self.current_model)
        self.model_menu = ctk.CTkOptionMenu(
            settings_row, variable=self.model_var, width=170, height=28,
            values=[self.MACHINE_TRANSLATION] + self.GEMINI_MODELS + self.OLLAMA_MODELS, 
            command=self.on_model_change,
            font=("Segoe UI", 11), 
            fg_color=THEME_DROPDOWN_BTN, 
            button_color=THEME_DROPDOWN_BTN,
            button_hover_color=THEME_DROPDOWN_HOVER, 
            dropdown_fg_color=THEME_BG,
            dropdown_hover_color=THEME_DROPDOWN_HOVER,
            corner_radius=8
        )
        self.model_menu.pack(side="left", padx=(0, 10))

        # Tools Group
        tools_frame = ctk.CTkFrame(settings_row, fg_color="transparent")
        tools_frame.pack(side="right")
        
        self.think_frame = ctk.CTkFrame(tools_frame, fg_color="transparent")
        self.think_frame.pack(side="left", padx=(0, 8))
        
        # Think Toggle
        self.think_var = ctk.StringVar(value="Auto")
        self.think_menu = ctk.CTkSegmentedButton(
            self.think_frame, values=["Auto", "🧠", "⚡"],
            variable=self.think_var, command=self.on_think_change,
            font=("Segoe UI", 10), width=90, height=24,
            fg_color="#333333", selected_color=ACCENT_PURPLE, selected_hover_color=ACCENT_PURPLE, corner_radius=6
        )
        self.think_menu.pack(side="left")

        # Utility Icons
        self.btn_auto = self.create_icon_btn(tools_frame, "⚡", self.toggle_auto_clip, "Auto-Clip", width=26, height=24)
        self.btn_auto.pack(side="left", padx=2)
        self.btn_pin = self.create_icon_btn(tools_frame, "📌", self.toggle_pin, "Pin", width=26, height=24)
        self.btn_pin.pack(side="left", padx=2)
        self.btn_opacity = self.create_icon_btn(tools_frame, "💧", self.toggle_opacity_slider, "Opacity", width=26, height=24)
        self.btn_opacity.pack(side="left", padx=2)

        # === 4. SLIDER (Hidden by default) ===
        self.slider_frame = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        self.slider = ctk.CTkSlider(self.slider_frame, from_=0.3, to=1.0, number_of_steps=20, 
                                   command=self.change_opacity, width=300, height=14, progress_color=ACCENT_PURPLE)
        self.slider.pack(pady=0)
        self.slider.set(1.0)
        
        # === 5. EDITOR AREA (Main Layout - GRID for equal splitting) ===
        editors_frame = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        editors_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        
        # Configure Grid Weights: Input (1), Output (1.5) to favor output area
        editors_frame.grid_rowconfigure(0, weight=1) # Input
        editors_frame.grid_rowconfigure(1, weight=2) # Output
        editors_frame.grid_columnconfigure(0, weight=1)
        
        # --- INPUT (Row 0) ---
        input_container = ctk.CTkFrame(editors_frame, fg_color=SECTION_BG, corner_radius=12, border_width=1, border_color="#222")
        input_container.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        
        in_head = ctk.CTkFrame(input_container, fg_color="transparent", height=28)
        in_head.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(in_head, text="INPUT", font=("Segoe UI", 10, "bold"), text_color="#555").pack(side="left")
        
        self.input_text = ctk.CTkTextbox(input_container, font=("Consolas", 12),
                                       fg_color="transparent", border_width=0, text_color="#CCC")
        self.input_text.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        self.input_text.bind("<KeyRelease>", self.on_key_release)
        self.input_text.insert("0.0", "Type or paste text here...")
        self.input_text.bind("<FocusIn>", self._clear_placeholder)
        
        # --- OUTPUT (Row 1) ---
        output_container = ctk.CTkFrame(editors_frame, fg_color=SECTION_BG, corner_radius=12, border_width=1, border_color="#332244") # Slight purple tint on border
        output_container.grid(row=1, column=0, sticky="nsew")
        
        out_head = ctk.CTkFrame(output_container, fg_color="transparent", height=28)
        out_head.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(out_head, text="RESULT", font=("Segoe UI", 10, "bold"), text_color="#8E44AD").pack(side="left")
        
        # Copy Button in Header
        self.btn_copy = ctk.CTkButton(out_head, text="📋 Copy", width=50, height=20, font=("", 10),
                                    fg_color="#222", hover_color="#333", command=self.do_copy_result)
        self.btn_copy.pack(side="right")
        
        self.think_indicator = ctk.CTkLabel(out_head, text="", font=("", 12), text_color="#8E44AD")
        self.think_indicator.pack(side="right", padx=6)
        
        self.output_text = ctk.CTkTextbox(output_container, font=("Consolas", 12),
                                         fg_color="transparent", border_width=0, text_color="#E0E0E0")
        self.output_text.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        # Bind to both main widget and internal textbox to ensure click is caught even when disabled
        self.output_text.bind("<Button-1>", self.on_output_click)
        if hasattr(self.output_text, "_textbox"):
            self.output_text._textbox.bind("<Button-1>", self.on_output_click)
            self.output_text._textbox.configure(cursor="hand2")

        # === 6. RESIZE GRIP ===
        self.grip = ctk.CTkLabel(self.outer_frame, text="◢", font=("Arial", 12), text_color="#333", cursor="size_nw_se")
        self.grip.place(relx=1.0, rely=1.0, anchor="se", x=-4, y=-4)
        self.grip.bind("<Button-1>", self.start_resize)
        self.grip.bind("<B1-Motion>", self.do_resize)

    def start_resize(self, event):
        self._resize_x = event.x_root
        self._resize_y = event.y_root
        self._start_width = self.winfo_width()
        self._start_height = self.winfo_height()

    def do_resize(self, event):
        delta_x = event.x_root - self._resize_x
        delta_y = event.y_root - self._resize_y
        new_width = max(420, self._start_width + delta_x)
        new_height = max(450, self._start_height + delta_y)
        self.geometry(f"{new_width}x{new_height}")

    def do_copy_result(self):
        self.on_output_click(None)

    def _clear_placeholder(self, event):
        if self.input_text.get("0.0", "end").strip() == "Type or paste text here...":
            self.input_text.delete("0.0", "end")
            self.input_text.configure(text_color="#E0E0E0")

    def create_icon_btn(self, parent, text, command, tooltip_text, width=32, height=32, fg_color="transparent"):
        btn = ctk.CTkButton(parent, text=text, width=width, height=height, 
                          fg_color=fg_color, border_width=0, 
                          hover_color="#333333",
                          command=command, font=("Segoe UI Emoji", 12), corner_radius=6)
        ToolTip(btn, tooltip_text)
        return btn

    def start_move(self, event):
        self._offsetx = event.x
        self._offsety = event.y

    def do_move(self, event):
        x = self.winfo_x() + event.x - self._offsetx
        y = self.winfo_y() + event.y - self._offsety
        self.geometry(f"+{x}+{y}")

    def minimize_window(self):
        self.update_idletasks()
        self.withdraw()
        self.after(10, self.iconify)
        # Handle showing in taskbar when de-iconifying
        self.bind("<Map>", lambda e: self.deiconify())

    def init_backends(self):
        """Initialize Ollama and Deep-Translator"""
        # 1. Initialize Machine Translation
        try:
            from deep_translator import GoogleTranslator
            self.translator = GoogleTranslator(source='auto', target='ko')
            logger.info("Deep-Translator initialized.")
        except Exception as e:
            logger.error(f"Failed to init Deep-Translator: {e}")

        # 2. Initialize Ollama
        try:
            import ollama
            
            # Check server connection and get available models
            models_response = ollama.list()
            available_models = [m.get('name', '').split(':')[0] + ':' + m.get('name', '').split(':')[-1] 
                              for m in models_response.get('models', [])]
            
            # Update model list with available models
            if available_models:
                self.after(0, lambda: self.update_model_list(available_models))
            
            self.ollama_ready = True
            self.update_status(f"모델 로딩 중 ({self.current_model})...")
            
            # Warm-up: Send a minimal request to pre-load the model
            ollama.chat(
                model=self.current_model,
                messages=[{'role': 'user', 'content': 'hi'}],
                options={'num_predict': 1}
            )
            self.update_status(f"✓ 준비 완료 ({self.current_model})")
            
        except Exception as e:
            self.ollama_ready = False
            error_msg = str(e)
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                self.update_status("❌ Ollama 서버가 실행되지 않음 (LLM 모드 사용 불가)")
            else:
                self.update_status(f"❌ Ollama 오류: {e}")
            logger.error(f"Ollama Init Error: {e}")

    def update_model_list(self, available_models):
        """Update model dropdown with available models"""
        all_ollama = list(set(available_models + self.OLLAMA_MODELS))
        all_ollama.sort()
        all_models = [self.MACHINE_TRANSLATION] + self.GEMINI_MODELS + all_ollama
        self.model_menu.configure(values=all_models)

    def update_status(self, msg):
        self.after(0, lambda: self.status_label.configure(text=msg))

    def on_model_change(self, choice):
        self.current_model = choice
        
        # Toggle Think frame visibility
        if choice == self.MACHINE_TRANSLATION:
            self.think_frame.pack_forget()
            self.update_status("🔄 기계 번역 모드 선택")
        else:
            self.think_frame.pack(side="right", padx=8, pady=4)
            if choice.startswith("✦ "):
                self.update_status(f"✦ Gemini 모델 선택: {choice.replace('✦ ', '')}")
            else:
                self.update_status(f"모델 변경: {choice}")
                threading.Thread(target=self._warmup_model, args=(choice,), daemon=True).start()

    def _warmup_model(self, model):
        if model.startswith("✦ ") or model == self.MACHINE_TRANSLATION:
            return
        try:
            import ollama
            self.update_status(f"모델 로딩 중 ({model})...")
            ollama.chat(
                model=model,
                messages=[{'role': 'user', 'content': 'hi'}],
                options={'num_predict': 1}
            )
            self.update_status(f"✓ 준비 완료 ({model})")
        except Exception as e:
            self.update_status(f"❌ 모델 로딩 실패: {e}")

    def on_think_change(self, choice):
        if choice == "Auto":
            self.force_think = None
        elif choice == "🧠 On":
            self.force_think = True
        else:
            self.force_think = False

    def get_think_mode(self, preset_name):
        if self.force_think is not None:
            return self.force_think
        _, default_think, _ = self.PRESETS.get(preset_name, ("", False, None))
        return default_think

    def on_output_click(self, event):
        try:
            text = self.output_text.get("0.0", "end").strip()
            if text:
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update()
                self.update_status("📋 복사됨!")
                
                bg = self.output_text.cget("fg_color")
                self.output_text.configure(fg_color="#2ECC71")
                self.after(200, lambda: self.output_text.configure(fg_color=bg))
        except: pass

    # --- Logic ---

    def on_preset_change(self, choice):
        if choice.startswith("-- "):
            # Revert if separator is clicked
            self.preset_var.set(self.current_preset)
            return

        self.current_preset = choice
        # Update think indicator
        use_think = self.get_think_mode(choice)
        self.think_indicator.configure(text="🧠" if use_think else ("⚡" if self.current_model != self.MACHINE_TRANSLATION else "🌐"))
        
        # Intelligent model switching
        _, _, target_lang = self.PRESETS.get(choice, (None, None, None))
        if target_lang and self.current_model == self.MACHINE_TRANSLATION:
             # Already in MT mode, just trigger
             pass
        elif target_lang and not self.ollama_ready and not self.gemini_api_key:
             # Fallback to MT if LLMs are not available
             self.model_var.set(self.MACHINE_TRANSLATION)
             self.on_model_change(self.MACHINE_TRANSLATION)
        
        self.trigger_check_debounce(delay=0.1)

    def on_key_release(self, event):
        if event.keysym in ["Up", "Down", "Left", "Right", "Shift_L", "Shift_R", "Control_L", "Control_R"]:
            return
        self.trigger_check_debounce(delay=2.5)

    def trigger_check_debounce(self, delay=2.5):
        if self.debounce_timer:
            self.after_cancel(self.debounce_timer)
        self.debounce_timer = self.after(int(delay * 1000), self.trigger_check_manual)

    def trigger_check_manual(self):
        text = self.input_text.get("0.0", "end").strip()
        if len(text) > self.MAX_CHARS:
            self.update_status(f"⚠️ 텍스트가 너무 깁니다 ({len(text)}/{self.MAX_CHARS}자)")
            return
            
        if text == self.last_input_text and self.current_preset == self.last_preset:
             # If text and preset are same, avoid reprocessing even if output is empty
             # unless the user explicitly clicked RUN (which bypasses this debounce anyway)
             return 

        self.last_input_text = text
        self.last_preset = self.current_preset
        
        self.request_counter += 1
        current_req_id = self.request_counter
        
        # Cancel any ongoing stream
        self.cancel_stream = True
        
        # Prevent multiple threads from starting the initial connection phase simultaneously
        if self.is_processing and self.current_model == self.MACHINE_TRANSLATION:
             # MT is not streaming, we can just wait or skip
             # For simplicity, we just let the last one win via request_counter
             pass

        if self.current_model == self.MACHINE_TRANSLATION:
            self.update_status(f"🌐 Google 번역 중... ({self.current_preset})")
            threading.Thread(target=self.run_machine_translation, args=(text, self.current_preset, current_req_id), daemon=True).start()
        else:
            use_think = self.get_think_mode(self.current_preset)
            
            # Cooldown check for Gemini
            if self.current_model.startswith("✦ "):
                import time
                if time.time() < self.gemini_cooldown_until:
                    remaining = int(self.gemini_cooldown_until - time.time())
                    self.update_status(f"⏳ Gemini 쿨다운 중... ({remaining}초 남음)")
                    return

            mode_str = "🧠 Thinking..." if use_think else "⚡ Processing..."
            self.update_status(f"{mode_str} ({self.current_preset})")
            self.think_indicator.configure(text="🧠" if use_think else "⚡")
            threading.Thread(target=self.run_refine_stream, args=(text, self.current_preset, current_req_id, use_think), daemon=True).start()

    def run_machine_translation(self, text, preset_name, req_id):
        """Run standard machine translation using deep-translator"""
        self.is_processing = True
        try:
            if not self.translator:
                self.after(0, lambda: self.update_status("❌ 번역 엔진 로드 실패"))
                return
                
            _, _, target_lang = self.PRESETS.get(preset_name, (None, None, "ko"))
            if not target_lang: target_lang = "ko"
            
            self.translator.target = target_lang
            result = self.translator.translate(text)
            
            if req_id == self.request_counter:
                self.after(0, lambda: self.show_result(result, f"✓ 번역 완료 ({target_lang.upper()})"))
        except Exception as e:
            if req_id == self.request_counter:
                err_msg = str(e)
                if "429" in err_msg or "too many requests" in err_msg.lower():
                    self.update_status("❌ Google 번역 할당량 초과 (잠시 후 시도)")
                else:
                    self.update_status(f"❌ 번역 오류: {e}")
            logger.error(f"MT Error: {e}")
        finally:
            self.is_processing = False

    def run_refine_stream(self, text, preset_name, req_id, use_think):
        """Run refinement with streaming output - supports Ollama and Gemini"""
        self.is_streaming = True
        self.is_processing = True
        self.cancel_stream = False
        
        try:
            prompt_template, _, _ = self.PRESETS.get(preset_name, ("Refine the following text:", False, None))
            full_prompt = f"{prompt_template}\n\nText:\n{text}"
            
            self.after(0, self._prepare_streaming_output)
            
            if self.current_model.startswith("✦ "):
                self._run_gemini_stream(full_prompt, preset_name, req_id)
            else:
                self._run_ollama_stream(full_prompt, preset_name, req_id, use_think)
                
        except Exception as e:
            if req_id == self.request_counter:
                self.update_status(f"❌ 오류: {e}")
            logger.error(f"Refine Stream Error: {e}")
        finally:
            self.is_streaming = False
            self.is_processing = False

    def _run_ollama_stream(self, full_prompt, preset_name, req_id, use_think):
        import ollama
        if use_think:
            system_prompt = "You are a professional editor. Think step by step before giving your answer. Output your final result after </think> tag."
        else:
            system_prompt = "/no_think\nYou are a professional editor. Output only the refined text without any explanation."
        
        stream = ollama.chat(
            model=self.current_model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': full_prompt}
            ],
            stream=True
        )
        
        in_think_block = False
        for chunk in stream:
            if self.cancel_stream or req_id != self.request_counter:
                break
            content = chunk.get('message', {}).get('content', '')
            if '<think>' in content:
                in_think_block = True
                content = content.split('<think>')[0]
            if '</think>' in content:
                in_think_block = False
                content = content.split('</think>')[-1]
            if not in_think_block and content:
                self.after(0, lambda c=content: self._append_streaming_text(c))
        
        if req_id == self.request_counter and not self.cancel_stream:
            self.after(0, lambda: self._finish_streaming(preset_name))

    def _run_gemini_stream(self, full_prompt, preset_name, req_id):
        if not self.gemini_api_key:
            self.update_status("❌ GEMINI_API_KEY가 설정되지 않음")
            return
        
        try:
            from google import genai
            model_name = self.current_model.replace("✦ ", "")
            if not self.gemini_client:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            
            system_prompt = "You are a professional editor. Output only the refined text without any explanation or conversational filler."
            response = self.gemini_client.models.generate_content_stream(
                model=model_name,
                contents=full_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                )
            )
            
            for chunk in response:
                if self.cancel_stream or req_id != self.request_counter:
                    break
                if chunk.text:
                    self.after(0, lambda c=chunk.text: self._append_streaming_text(c))
            
            if req_id == self.request_counter and not self.cancel_stream:
                self.after(0, lambda: self._finish_streaming(preset_name + " ✦"))
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                import time
                self.gemini_cooldown_until = time.time() + 30  # 30 second cooldown
                self.update_status("❌ Gemini API 할당량 초과 (30초 후 재시도 가능)")
                logger.warning("Gemini 429 RESOURCE_EXHAUSTED - Starting 30s cooldown.")
            else:
                self.update_status(f"❌ Gemini 오류: {e}")
            logger.error(f"Gemini Error: {e}")

    def _prepare_streaming_output(self):
        self.output_text.configure(state="normal")
        self.output_text.delete("0.0", "end")

    def _append_streaming_text(self, text):
        self.output_text.insert("end", text)
        self.output_text.see("end")

    def _finish_streaming(self, preset_name):
        self.output_text.configure(state="disabled")
        self.update_status(f"✓ 완료 ({preset_name})")

    def show_result(self, result, msg):
        self.output_text.configure(state="normal")
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", result)
        self.output_text.configure(state="disabled")
        self.update_status(msg)

    # --- Clipboard / Win Utils ---

    def start_clipboard_poll(self):
        self.check_clipboard()
        
    def check_clipboard(self):
        if self.is_auto_clip:
            try:
                clip_text = self.clipboard_get().strip()
                
                # Strict change detection
                if clip_text and clip_text != self.last_clipboard_text:
                    self.last_clipboard_text = clip_text
                    
                    current_input = self.input_text.get("0.0", "end").strip()
                    if clip_text != current_input:
                        out_text = self.output_text.get("0.0", "end").strip()
                        if clip_text != out_text:
                            self.input_text.delete("0.0", "end")
                            self.input_text.insert("0.0", clip_text)
                            self.trigger_check_debounce(delay=1.5)
            except: pass
        self.after(1000, self.check_clipboard)

    def toggle_auto_clip(self):
        self.is_auto_clip = not self.is_auto_clip
        if self.is_auto_clip:
            self.btn_auto.configure(fg_color="#F39C12", border_width=0)
            self.update_status("⚡ 자동 붙여넣기: ON")
        else:
            self.btn_auto.configure(fg_color="transparent", border_width=1)
            self.update_status("자동 붙여넣기: OFF")

    def toggle_opacity_slider(self):
        self.opacity_slider_visible = not self.opacity_slider_visible
        if self.opacity_slider_visible:
            self.slider_frame.pack(after=self.header_frame, fill="x", padx=12, pady=(0, 10))
            self.btn_opacity.configure(fg_color="#9B59B6", border_width=0)
        else:
            self.slider_frame.pack_forget()
            self.btn_opacity.configure(fg_color="transparent", border_width=0)

    def change_opacity(self, value):
        self.attributes('-alpha', value)

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes('-topmost', self.is_pinned)
        if self.is_pinned:
            self.btn_pin.configure(fg_color="#3498DB", border_width=0)
        else:
            self.btn_pin.configure(fg_color="transparent", border_width=1)

    def on_closing(self):
        self.cancel_stream = True
        self.destroy()

if __name__ == "__main__":
    app = AITextLabApp()
    app.mainloop()
