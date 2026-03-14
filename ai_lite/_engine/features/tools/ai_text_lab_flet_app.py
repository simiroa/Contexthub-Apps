import flet as ft
import sys
import threading
import time
from pathlib import Path

# Add legay root to path
APP_ROOT = Path(__file__).resolve().parent.parent.parent.parent # Apps/ai_lite
_engine_root = APP_ROOT / "_engine"
if str(_engine_root) not in sys.path:
    sys.path.insert(0, str(_engine_root))

from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from contexthub.ui.flet.theme import configure_page
from utils.i18n import t

from ai_text_lab_service import AITextLabService
from ai_text_lab_state import AITextLabState

class AITextLabFletApp:
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
    GEMINI_MODELS = ["✦ gemini-2.5-flash", "✦ gemini-2.0-flash"]
    DEFAULT_OLLAMA = ["qwen3:8b", "qwen3:4b", "llama3.2:3b", "gemma3:4b"]

    def __init__(self):
        self.service = AITextLabService()
        self.state = AITextLabState()
        self.cancel_event = threading.Event()

    def run(self):
        ft.app(target=self.main)

    def main(self, page: ft.Page):
        self.page = page
        configure_page(page, "AI Text Lab")
        
        # Async Backend Init
        self.update_status("Initializing...")
        threading.Thread(target=self.init_backend_task, daemon=True).start()
        
        self.build_ui()
        self.start_clipboard_poll()

    def init_backend_task(self):
        ollama_models = self.service.list_ollama_models()
        self.state.available_models = [self.MACHINE_TRANSLATION] + self.GEMINI_MODELS + (ollama_models if ollama_models else self.DEFAULT_OLLAMA)
        self.page.run_task(self.update_model_dropdown)
        
        if self.state.current_model in self.state.available_models:
             self.service.warmup_model(self.state.current_model)
        self.update_status("Ready")

    async def update_model_dropdown(self):
        self.model_dropdown.options = [ft.dropdown.Option(m) for m in self.state.available_models]
        self.page.update()

    def build_ui(self):
        self.page.clean()

        # --- Top Header Section ---
        self.preset_dropdown = ft.Dropdown(
            value=self.state.current_preset,
            options=[ft.dropdown.Option(k) for k in self.PRESETS.keys()],
            on_select=self.on_preset_change,
            expand=True,
            height=45,
            bgcolor=COLORS["field_bg"],
            text_size=14,
            border_radius=RADII["sm"],
        )

        self.run_btn = ft.ElevatedButton(
            "RUN PROCESS",
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            on_click=self.on_run_click,
            height=45,
            bgcolor=ft.Colors.ORANGE_800,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )

        header_row = ft.Container(
            content=ft.Row([self.preset_dropdown, self.run_btn], spacing=10),
            padding=SPACING["sm"],
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
        )

        # --- Settings Row ---
        self.model_dropdown = ft.Dropdown(
            value=self.state.current_model,
            options=[ft.dropdown.Option(m) for m in (self.state.available_models or [self.state.current_model])],
            on_select=self.on_model_change,
            width=200,
            height=35,
            text_size=12,
            bgcolor=COLORS["field_bg"],
        )

        self.think_toggle = ft.Dropdown(
            value=self.state.think_mode,
            options=[
                ft.dropdown.Option("Auto"),
                ft.dropdown.Option("On"),
                ft.dropdown.Option("Off"),
            ],
            on_select=self.on_think_toggle_change,
            width=100,
            height=35,
            text_size=12,
            bgcolor=COLORS["field_bg"],
        )

        self.utility_row = ft.Row(
            [
                ft.IconButton(ft.Icons.BOLT, on_click=self.toggle_auto_clip, tooltip="Auto-Paste"),
                ft.IconButton(ft.Icons.PUSH_PIN_OUTLINED, on_click=self.toggle_pin, tooltip="Pin on top"),
            ],
            spacing=0,
        )

        settings_row = ft.Row(
            [
                ft.Row([ft.Text("Model", size=12, weight="bold"), self.model_dropdown], spacing=5),
                ft.Row([self.think_toggle, self.utility_row], spacing=10),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # --- Editor Area ---
        self.input_box = ft.TextField(
            multiline=True,
            expand=True,
            hint_text="Type or paste text here...",
            on_change=self.on_input_change,
            bgcolor=COLORS["surface_alt"],
            border_color=COLORS["line"],
            text_size=13,
        )

        self.output_box = ft.TextField(
            multiline=True,
            expand=2,
            read_only=True,
            bgcolor=COLORS["surface_alt"],
            border_color=ft.Colors.with_opacity(0.1, COLORS["accent"]),
            text_size=13,
            suffix=ft.IconButton(ft.Icons.COPY, on_click=self.on_copy_click),
        )

        self.status_bar = ft.Text(self.state.status_msg, size=11, color=COLORS["text_soft"])

        self.page.add(
            header_row,
            ft.Container(content=settings_row, padding=ft.padding.only(left=5, right=5)),
            ft.Column([
                ft.Text("INPUT", size=10, weight="bold", color=COLORS["text_soft"]),
                self.input_box,
                ft.Row([
                    ft.Text("RESULT", size=10, weight="bold", color=COLORS["accent"]),
                    ft.ProgressBar(visible=False, width=100, color=COLORS["accent"]),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.output_box,
                self.status_bar,
            ], expand=True, spacing=5)
        )

    # --- Handlers ---
    def on_preset_change(self, e):
        choice = self.preset_dropdown.value
        if choice.startswith("-- "):
            self.preset_dropdown.value = self.state.current_preset
            self.page.update()
            return
        self.state.current_preset = choice
        self.trigger_process_debounce()

    def on_run_click(self, e):
        self.process_text()

    def on_model_change(self, e):
        self.state.current_model = self.model_dropdown.value
        self.update_status(f"Model changed to {self.state.current_model}")
        threading.Thread(target=lambda: self.service.warmup_model(self.state.current_model), daemon=True).start()

    def on_think_toggle_change(self, e):
        self.state.think_mode = self.think_toggle.value
        self.page.update()

    def on_input_change(self, e):
        self.state.input_text = self.input_box.value
        self.trigger_process_debounce()

    def trigger_process_debounce(self):
        # In Flet, we can use a simple threading timer for debounce if needed, 
        # but for now let's focus on manual and simple change triggers.
        pass

    def update_status(self, msg):
        self.state.status_msg = msg
        if hasattr(self, 'status_bar'):
            self.status_bar.value = msg
            self.page.update()

    def process_text(self):
        text = self.input_box.value.strip()
        if not text or text == "Type or paste text here...": return
        
        self.state.is_processing = True
        self.cancel_event.set() # Stop any current
        self.cancel_event.clear()
        
        self.output_box.value = ""
        self.update_status("Processing...")
        self.page.update()

        threading.Thread(target=self.run_task, args=(text, self.state.current_preset, self.state.current_model), daemon=True).start()

    def run_task(self, text, preset_name, model_name):
        try:
            if model_name == self.MACHINE_TRANSLATION:
                _, _, target_lang = self.PRESETS.get(preset_name, (None, None, "ko"))
                result = self.service.translate(text, target_lang or "ko")
                self.page.run_task(lambda: self.finish_task(result))
            else:
                prompt_template, default_think, _ = self.PRESETS.get(preset_name, ("Refine:", False, None))
                use_think = self.state.get_effective_think_mode(default_think)
                
                system_prompt = "You are a professional editor. "
                if use_think:
                     system_prompt += "Think step by step before giving your answer. Output your final result after </think> tag."
                else:
                     system_prompt += "Output only the refined text without any explanation."
                
                full_prompt = f"{prompt_template}\n\nText:\n{text}"
                
                if model_name.startswith("✦ "):
                    self.service.stream_gemini(model_name, system_prompt, full_prompt, self.append_output, self.cancel_event)
                else:
                    self.service.stream_ollama(model_name, system_prompt, full_prompt, 0, self.append_output, self.cancel_event)
                
                self.update_status(f"✓ Completed ({preset_name})")
        except Exception as e:
            self.update_status(f"❌ Error: {e}")

    def append_output(self, chunk):
        self.output_box.value += chunk
        self.page.update()

    def finish_task(self, result):
        self.output_box.value = result
        self.update_status("✓ Completed")
        self.page.update()

    def toggle_auto_clip(self, e):
        self.state.is_auto_clip = not self.state.is_auto_clip
        e.control.icon = ft.Icons.BOLT if self.state.is_auto_clip else ft.Icons.BOLT_OUTLINED
        self.update_status(f"Auto-Paste: {'ON' if self.state.is_auto_clip else 'OFF'}")
        self.page.update()

    def toggle_pin(self, e):
        self.state.is_pinned = not self.state.is_pinned
        self.page.window.always_on_top = self.state.is_pinned
        e.control.icon = ft.Icons.PUSH_PIN if self.state.is_pinned else ft.Icons.PUSH_PIN_OUTLINED
        self.page.update()

    def on_copy_click(self, e):
        if self.output_box.value:
            self.page.set_clipboard(self.output_box.value)
            self.page.open(ft.SnackBar(ft.Text("Result copied to clipboard")))

    def start_clipboard_poll(self):
        def poll():
            last_text = ""
            while True:
                if self.state.is_auto_clip:
                    # Flet's clipboard access is async/needs page. 
                    # For simplicity in this worker, we might skip or use a different library 
                    # if tight integration is needed. For now, we'll keep it as a placeholder 
                    # as true background clipboard polling in Flet is tricky without a hidden window or system hooks.
                    pass
                time.sleep(1)
        # threading.Thread(target=poll, daemon=True).start() # Optional

def open_ai_text_lab_flet():
    app = AITextLabFletApp()
    app.run()

if __name__ == "__main__":
    open_ai_text_lab_flet()
