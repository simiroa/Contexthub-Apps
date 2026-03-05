
import customtkinter as ctk
import threading
import sys
import os
import json
import time
import shutil
import random
import webbrowser
from pathlib import Path

# Add src to path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from features.comfyui.premium import PremiumComfyWindow, Colors, Fonts, GlassFrame, PremiumLabel, ActionButton, PremiumScrollableFrame
from utils.gui_lib import THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER
from features.comfyui.core.wrappers import registry
from features.comfyui.ui.widgets import ValueSliderWidget, PromptStackWidget, TagSelectorWidget
from manager.helpers.comfyui_client import ComfyUIManager
from utils.ai_helper import refine_text_ai
from utils.i18n import t

try:
    from utils.audio_player import AudioPlayer
except ImportError:
    AudioPlayer = None

class ControlKnob(ctk.CTkFrame):
    """A vertical slider that looks a bit more like a mixing console fader."""
    def __init__(self, parent, label, from_=0, to=100, default=50, res=1, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.pack(fill="x", pady=8)
        
        # Header (Label + Value)
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", pady=(0, 2))
        
        ctk.CTkLabel(head, text=label, font=Fonts.SMALL, text_color=Colors.TEXT_SECONDARY).pack(side="left")
        self.val_lbl = ctk.CTkLabel(head, text=str(default), font=("Segoe UI", 11, "bold"), text_color=Colors.ACCENT_PRIMARY)
        self.val_lbl.pack(side="right")
        
        self.res = res
        self.slider = ctk.CTkSlider(self, from_=from_, to=to, number_of_steps=(to-from_)/res, 
                                   progress_color=Colors.ACCENT_PRIMARY, button_color=Colors.ACCENT_PRIMARY,
                                   button_hover_color=Colors.ACCENT_SECONDARY, height=18, command=self.update_val)
        self.slider.set(default)
        self.slider.pack(fill="x")

    def update_val(self, val):
        v = round(val / self.res) * self.res
        txt = f"{v:.0f}" if self.res >= 1 else f"{v:.2f}"
        self.val_lbl.configure(text=txt)

    def get_value(self):
        return self.slider.get()

class ACEAudioEditorGUI(PremiumComfyWindow):
    """
    Creative Audio Studio (ACE) - 'Mixing Console' Edition
    Focused on parameter control and composition, not visualization.
    """
    def __init__(self, target_path=None):
        super().__init__(title=t("comfyui.ace_audio.title"), width=1200, height=800)
        
        self.target_path = target_path
        self.client = ComfyUIManager()
        default_key = "ace_edit" if target_path else "ace_song"
        self.wrapper = registry.get_by_key(default_key)
        
        # State
        self.is_processing = False
        self.is_playing = False
        self.player = AudioPlayer() if AudioPlayer else None
        self.last_output_path = None
        self.widgets = {}

        self._check_model()
        self._setup_console_layout()

    def _check_model(self):
        model_path = self.client.comfy_dir / "models" / "checkpoints" / "ace_step_v1_3.5b.safetensors"
        if not model_path.exists():
            self.after(1000, lambda: self.status_badge.set_status("CORE MISSING", "error"))

    def _setup_console_layout(self):
        # Reset grid from Premium Window
        self.content_area.grid_columnconfigure(0, weight=3) # Composition (Left)
        self.content_area.grid_columnconfigure(1, weight=2) # Rack (Right)
        
        # --- LEFT: COMPOSITION AREA ---
        self.frame_comp = GlassFrame(self.content_area)
        self.frame_comp.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        
        # 1. FIXED HEADER (Control Deck)
        self.comp_header = ctk.CTkFrame(self.frame_comp, fg_color="transparent", height=80)
        self.comp_header.pack(fill="x", padx=15, pady=15)
        
        # Row 1: Title + Mode
        h_row1 = ctk.CTkFrame(self.comp_header, fg_color="transparent")
        h_row1.pack(fill="x", pady=(0, 10))
        PremiumLabel(h_row1, text=t("comfyui.ace_audio.composition"), style="header").pack(side="left")
        
        self.combo_preset = ctk.CTkComboBox(h_row1, width=220, height=28,
                                           values=[t("comfyui.ace_audio.preset_vocal"), t("comfyui.ace_audio.preset_inst"), t("comfyui.ace_audio.preset_edit")],
                                           command=self._on_preset_change,
                                           fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, border_color=THEME_DROPDOWN_BTN)
        self.combo_preset.set(self.wrapper.name)
        self.combo_preset.pack(side="right")
        
        # WebUI Link
        self.btn_webui = ctk.CTkButton(h_row1, text="🌐 WebNode", width=80, height=28, fg_color="#333", 
                                      hover_color="#444", font=Fonts.SMALL, command=self.open_webui)
        self.btn_webui.pack(side="right", padx=(0, 10))

        # Row 2: Global Helpers (Genre Preset)
        self.genre_row = ctk.CTkFrame(self.comp_header, fg_color="transparent")
        # Only packed if relevant (in _build_interface)
        
        # Divider
        ctk.CTkFrame(self.frame_comp, height=1, fg_color="#333").pack(fill="x", padx=15)

        # 2. SCROLLING CONTENT
        self.scroll_comp = PremiumScrollableFrame(self.frame_comp, fg_color="transparent")
        self.scroll_comp.pack(fill="both", expand=True, padx=10, pady=10)

        # --- RIGHT: RACK & TRANSPORT ---
        self.frame_rack = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.frame_rack.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=(0, 20))
        
        # 1. Parameter Rack
        self.rack_box = GlassFrame(self.frame_rack)
        self.rack_box.pack(fill="both", expand=True, pady=(0, 10))
        
        PremiumLabel(self.rack_box, text=t("comfyui.ace_audio.mixing_rack"), style="header").pack(anchor="w", padx=15, pady=15)
        self.rack_params = ctk.CTkFrame(self.rack_box, fg_color="transparent")
        self.rack_params.pack(fill="both", expand=True, padx=15, pady=5)
        
        # 2. Transport (Bottom Right)
        self.transport_box = GlassFrame(self.frame_rack)
        self.transport_box.pack(fill="x")
        
        self.btn_run = ActionButton(self.transport_box, text=t("comfyui.ace_audio.synth_btn"), variant="magic", height=60, command=self.start_generation)
        self.btn_run.pack(fill="x", padx=15, pady=(15, 10))
        
        self.status_lbl = ctk.CTkLabel(self.transport_box, text=t("comfyui.ace_audio.ready"), font=Fonts.SMALL, text_color="gray")
        self.status_lbl.pack(pady=(0, 15))

        # Player Controls (Initially Hidden)
        self.player_controls = ctk.CTkFrame(self.transport_box, fg_color="transparent")
        
        self.btn_play = ctk.CTkButton(self.player_controls, text="▶ " + t("comfyui.ace_audio.play"), width=100, fg_color=Colors.ACCENT_PRIMARY, text_color="#000", hover_color="#69F0AE", command=self.toggle_play)
        self.btn_play.pack(side="left", padx=5)
        
        self.lbl_time = ctk.CTkLabel(self.player_controls, text="--:--", font=Fonts.SMALL)
        self.lbl_time.pack(side="right", padx=5)
        
        # Initial Build
        self._build_interface()

    def _on_preset_change(self, name):
        self.wrapper = registry.get_by_name(name)
        self._build_interface()

    def _build_interface(self):
        # Clear previous
        for w in self.scroll_comp.winfo_children(): w.destroy()
        for w in self.rack_params.winfo_children(): w.destroy()
        for w in self.genre_row.winfo_children(): w.destroy() # Clear genre row
        self.genre_row.pack_forget() # Hide by default
        
        self.widgets = {}

        ui_defs = self.wrapper.get_ui_definition()
        
        # Separate sliders and text areas
        sliders = [d for d in ui_defs if d.type == "slider"]
        files = [d for d in ui_defs if d.key == "audio_input"]
        
        # --- BUILD COMPOSTION (Text + Dropdowns + Tags) ---
        
        # 1. Style Config Helper (If song or instrumental) -> Now in Header!
        if "Song" in self.wrapper.name or "Instrumental" in self.wrapper.name:
            self.genre_row.pack(fill="x", pady=(5, 0)) # Show header row
            self._build_style_helper_in_header()

        # 2. Build Text Inputs with Special Logic
        for d in ui_defs:
            if d.type != "text": continue
            
            is_lyrics = "lyrics" in d.key.lower() or "tags" in d.key.lower()
            refine_type = "lyrics" if is_lyrics else "prompt"
            d_label = d.label.upper()
            
            # LYRICS: Use Section-Aware Stack
            if is_lyrics:
                # Sections options
                opts = ["Verse", "Chorus", "Intro", "Outro", "Bridge", "Drop", "Build-up"]
                w = PromptStackWidget(self.scroll_comp, d_label, 
                                     on_refine_handler=lambda x, t=refine_type: self._ai_refine_logic(x, t),
                                     layer_options=opts)
                w.layers[0].set_text(d.default)
                w.pack(fill="x", pady=(10, 15))
                self.widgets[d.key] = w
            
            # INSTRUMENTS/STYLE: Use Tags + Stack
            else:
                # Add a Tag Selector for ease of use
                if "Instrumental" in self.wrapper.name:
                    tags = ["Piano", "Guitar", "Synth", "Bass", "Drums", "Strings", "Brass", "Lo-fi", "Orchestral"]
                    t = TagSelectorWidget(self.scroll_comp, tags, label="INSTRUMENT SELECTOR")
                    self.widgets["_tags_" + d.key] = t # Internal key
                
                # Standard Text (Style)
                w = PromptStackWidget(self.scroll_comp, d_label, 
                                     on_refine_handler=lambda x, t=refine_type: self._ai_refine_logic(x, t),
                                     layer_options=["Style", "Mood", "Genre", "Instrument"])
                w.layers[0].set_text(d.default)
                w.pack(fill="x", pady=(10, 15))
                self.widgets[d.key] = w


        # --- BUILD RACK (Sliders & Files) ---
        for d in files:
            f = ctk.CTkFrame(self.rack_params, fg_color=Colors.BG_CARD, corner_radius=6, border_width=1, border_color="#333")
            f.pack(fill="x", pady=10)
            PremiumLabel(f, text="INPUT SOURCE", style="small").pack(anchor="w", padx=10, pady=5)
            self.lbl_file = ctk.CTkLabel(f, text=Path(self.target_path).name if self.target_path else "No Audio File", font=Fonts.BODY)
            self.lbl_file.pack(padx=10)
            ctk.CTkButton(f, text="Load File", height=24, fg_color="#333", command=self.select_file).pack(pady=10)

        for d in sliders:
            w = ControlKnob(self.rack_params, d.label.upper(), from_=d.options["from"], to=d.options["to"], 
                           default=d.default, res=d.options["res"])
            self.widgets[d.key] = w

    def _build_style_helper_in_header(self):
        genres = ["Pop: K-Pop, Energetic", "Rock: Electric Guitar, Heavy Drums", 
                  "Jazz: Smooth, Piano, Saxophone", "Lo-Fi: Chill, Hip Hop, Study",
                  "EDM: Synthesizer, Bass Drop", "Orchestral: Cinematic, Epic"]
        
        combo = ctk.CTkComboBox(self.genre_row, values=genres, width=280, height=28, 
                               font=Fonts.BODY, command=self._apply_genre_preset,
                               fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, border_color=THEME_DROPDOWN_BTN)
        combo.set("⚡ Quick Style Preset...")
        combo.pack(side="left", fill="x", expand=True)

    def _apply_genre_preset(self, val):
        # Find the style widget and inject text
        style_key = "style_prompt" if "style_prompt" in self.widgets else None
        if not style_key and "input_text" in self.widgets: style_key = "input_text" # Fallback
        
        if style_key and ":" in val:
            genre, desc = val.split(":", 1)
            # Add as a new layer or replace first? Let's add new layer for "Genre"
            widget = self.widgets[style_key]
            widget.add_layer(f"{genre.strip()} - {desc.strip()}")

    def _ai_refine_logic(self, widget, type):
        original = widget.get_text()
        if not original: return
        widget.btn_refine.configure(text="⏳", state="disabled")
        self.status_badge.set_status("AI Analyzing...", "active")
        
        def _cb(res, err=None):
            self.after(0, lambda: widget.btn_refine.configure(text="✨", state="normal"))
            if res:
                self.after(0, lambda: widget.set_text(res))
                self.after(0, lambda: self.status_badge.set_status("Refined", "success"))
            else:
                self.after(0, lambda: self.status_badge.set_status("AI Failed", "error"))

        refine_text_ai(original, type=type, callback=_cb)

    def open_webui(self):
        # 1. Generate Current Workflow
        try:
            val = {}
            for k, w in self.widgets.items():
                if k.startswith("_tags_"): continue 
                if isinstance(w, PromptStackWidget): 
                    text_part = w.get_combined_text()
                    tag_key = "_tags_" + k
                    if tag_key in self.widgets:
                        tags = self.widgets[tag_key].get_value()
                        if tags: text_part = f"{tags}, {text_part}" if text_part else tags
                    val[k] = text_part
                elif isinstance(w, ControlKnob): val[k] = w.get_value()
                else: val[k] = w.get_value()

            if self.wrapper.name == "ACE Audio Repaint (Edit)" and self.target_path:
                val["audio_input"] = Path(self.target_path).name

            if val.get("seed") == 0 or "seed" not in val: val["seed"] = random.randint(1, 2**32-1)
            
            with open(src_dir / self.wrapper.workflow_path, 'r', encoding='utf-8') as f: 
                base_workflow = json.load(f)
            
            final_workflow = self.wrapper.apply_values(base_workflow, val)
            json_str = json.dumps(final_workflow, indent=2)

            # 2. Copy
            self.clipboard_clear()
            self.clipboard_append(json_str)
            self.update()
            
            # 3. Notify
            self.status_badge.set_status(t("comfyui.common.copied"), "success")
        except Exception as e:
            print(f"[WARN] Failed to copy workflow: {e}")

        # 4. Open
        url = self.get_server_url()
        webbrowser.open(url)
        # self.status_badge.set_status("WebUI Opened", "success") -> Overwritten by copy status

    def select_file(self):
        from tkinter import filedialog
        f = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3;*.wav")])
        if f:
            self.target_path = f
            self.lbl_file.configure(text=Path(f).name)

    def start_generation(self):
        if self.is_processing: return
        val = {}
        # Gather inputs
        for k, w in self.widgets.items():
            if k.startswith("_tags_"): continue # Handled inside style
            
            if isinstance(w, PromptStackWidget): 
                # Combine Text Stack + Tag Cloud (if exists for this key)
                text_part = w.get_combined_text()
                tag_key = "_tags_" + k
                if tag_key in self.widgets:
                    tags = self.widgets[tag_key].get_value()
                    if tags: text_part = f"{tags}, {text_part}" if text_part else tags
                val[k] = text_part
            
            elif isinstance(w, ControlKnob): val[k] = w.get_value()
            else: val[k] = w.get_value() # fallback

        if self.wrapper.name == "ACE Audio Repaint (Edit)":
            if not self.target_path: return
            val["audio_input"] = Path(self.target_path).name
            shutil.copy(self.target_path, self.client.comfy_dir / "input" / val["audio_input"])

        if val.get("seed") == 0: val["seed"] = random.randint(1, 2**32-1)

        self.is_processing = True
        self.btn_run.configure(state="disabled", text=t("comfyui.common.processing"))
        self.status_badge.set_status(t("comfyui.common.synthesizing"), "active")
        self.status_lbl.configure(text=t("comfyui.common.processing"), text_color=Colors.ACCENT_PRIMARY)
        
        threading.Thread(target=self._run_thread, args=(val,), daemon=True).start()

    def _run_thread(self, val):
        try:
            with open(src_dir / self.wrapper.workflow_path, 'r', encoding='utf-8') as f: workflow = json.load(f)
            api_workflow = self.wrapper.apply_values(workflow, val)
            self.client.generate_image(api_workflow) 
            time.sleep(2)
            
            # Polling (Same as before)
            output_root = self.client.comfy_dir / "output"
            # Simple polling loop (max 60s)
            start_t = time.time()
            target_file = None
            
            while time.time() - start_t < 60:
                recent_files = sorted(output_root.glob("**/*.mp3"), key=os.path.getmtime, reverse=True)
                if recent_files:
                    latest = recent_files[0]
                    if time.time() - os.path.getmtime(latest) < 20: 
                        target_file = latest
                        break
                time.sleep(1)
                
            if not target_file: raise Exception("Timeout: No audio generated.")
            
            dest = Path("outputs/ace_studio") / f"ace_mix_{int(time.time())}.mp3"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(target_file, dest)
            self.after(0, lambda: self._on_success(str(dest)))
        except Exception as e: self.after(0, lambda: self._on_error(str(e)))

    def _on_success(self, path):
        self.is_processing = False
        self.last_output_path = path
        self.btn_run.configure(state="normal", text=t("comfyui.ace_audio.synth_btn"))
        self.status_badge.set_status(t("comfyui.ace_audio.mix_ready"), "success")
        self.status_lbl.configure(text=f"Saved: {Path(path).name}", text_color=Colors.ACCENT_GREEN)
        
        self.player_controls.pack(fill="x", padx=15, pady=10)
        self.btn_play.configure(text="▶ " + t("comfyui.ace_audio.play_mix"))

    def _on_error(self, msg):
        self.is_processing = False
        self.btn_run.configure(state="normal", text="RETRY SYNTHESIS")
        self.status_badge.set_status(t("comfyui.ace_audio.engine_error"), "error")
        self.status_lbl.configure(text=f"Error: {msg[:40]}...", text_color=Colors.ACCENT_ERROR)

    def toggle_play(self):
        if not self.last_output_path: return
        if self.is_playing:
            if self.player: self.player.stop()
            self.is_playing = False
            self.btn_play.configure(text="▶ " + t("comfyui.ace_audio.play_mix"), fg_color=Colors.ACCENT_PRIMARY)
        else:
            if not self.player:
                os.startfile(self.last_output_path)
                return
            success = self.player.play(self.last_output_path, on_stop_callback=self._on_playback_end)
            if success:
                self.is_playing = True
                self.btn_play.configure(text="⏹ " + t("comfyui.ace_audio.stop"), fg_color=Colors.ACCENT_ERROR)

    def _on_playback_end(self):
        self.after(0, lambda: self.btn_play.configure(text="▶ " + t("comfyui.ace_audio.play_mix"), fg_color=Colors.ACCENT_PRIMARY))
        self.is_playing = False

if __name__ == "__main__":
    app = ACEAudioEditorGUI()
    app.mainloop()
