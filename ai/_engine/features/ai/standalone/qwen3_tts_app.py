import json
import os
import tempfile
import threading
import time
import wave
import winsound
from array import array
from pathlib import Path

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox

from utils import paths
from utils.ai_runner import kill_process_tree, start_ai_script
from utils.gui_lib import BaseWindow, THEME_ACCENT, THEME_BORDER, THEME_BTN_HOVER, THEME_BTN_PRIMARY, THEME_CARD, THEME_DROPDOWN_BTN, THEME_DROPDOWN_FG, THEME_DROPDOWN_HOVER, THEME_TEXT_DIM, THEME_TEXT_MAIN
from utils.i18n import t

SUPPORTED_SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]
SUPPORTED_LANGUAGES = ["Auto", "Chinese", "English", "Japanese", "Korean", "German", "French", "Russian", "Portuguese", "Spanish", "Italian"]
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac"}
TONE_PRESETS = {
    "natural": t("qwen3_tts.style_natural_text", "Speak naturally with clear pacing and a calm, confident tone."),
    "warm": t("qwen3_tts.style_warm_text", "Use a warm, friendly tone with gentle emphasis and smooth phrasing."),
    "energetic": t("qwen3_tts.style_energetic_text", "Deliver the line with bright energy, crisp emphasis, and upbeat pacing."),
    "precise": t("qwen3_tts.style_precise_text", "Use precise diction, short pauses, and a clean professional delivery."),
}
PROFILE_FILE = paths.QWEN_TTS_DIR / "profiles.json"
PROFILE_COLORS = ["#3B82F6", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#06B6D4", "#F97316"]
STATUS_COLORS = {"ready": "#64748B", "queued": "#F59E0B", "done": "#10B981", "error": "#EF4444"}


class Qwen3TTSGUI(BaseWindow):
    def __init__(self, target_path=None):
        super().__init__(title="qwen3_tts.title", width=980, height=900, scrollable=False, icon_name="audio_generate")
        self.target_path = Path(target_path) if target_path else None
        self.current_process = None
        self.pending_jobs_file = None
        self.latest_outputs = []
        self.messages = []
        self.selected_message_id = None
        self.expanded_actions_message_id = None
        self.expanded_text_editor_message_id = None
        self.overlay_after_id = None
        self.language_var = ctk.StringVar(value="Auto")
        self.device_var = ctk.StringVar(value="cuda")
        self.profile_var = ctk.StringVar()
        self.tone_var = ctk.StringVar(value="natural")
        self.status_var = ctk.StringVar(value=t("common.ready", "Ready"))
        self.advanced_open = False
        self.total_jobs = 0
        self.completed_jobs = 0
        self.current_playback_path = None
        self.current_playback_started_at = None
        self.current_playback_duration = 0.0
        self.playback_after_id = None
        self.waveform_views = {}
        self.profile_panel_visible = False
        self.profile_editor_target_id = None
        default_output = Path.home() / "Documents"
        self.output_dir = Path(default_output if default_output.exists() else Path.home())
        self.profiles = self._load_profiles()
        self.profile_var.set(self.profiles[0]["name"])
        self._build_ui()
        self._prefill_from_target()
        self._render_messages()
        self._refresh_status_bar()

    def _profile_color(self, profile_name):
        try:
            idx = self._profile_names().index(profile_name)
        except ValueError:
            idx = 0
        return PROFILE_COLORS[idx % len(PROFILE_COLORS)]

    def _profile_mode_label(self, mode):
        labels = {
            "custom_voice": t("qwen3_tts.mode_custom", "Preset Voice"),
            "voice_clone": t("qwen3_tts.mode_clone", "Clone from Audio"),
            "voice_design": t("qwen3_tts.mode_design", "Design New Voice"),
        }
        return labels.get(mode, mode)

    def _status_label(self, status):
        labels = {
            "ready": t("qwen3_tts.status_ready", "Ready"),
            "queued": t("qwen3_tts.status_queued", "Queued"),
            "done": t("qwen3_tts.status_done_short", "Done"),
            "error": t("qwen3_tts.status_error_short", "Error"),
        }
        return labels.get(status, status)

    def _default_profiles(self):
        return [
            {"id": "narrator", "name": t("qwen3_tts.profile_narrator", "Narrator"), "mode": "custom_voice", "speaker": "Vivian", "instruct": TONE_PRESETS["natural"], "ref_audio": "", "ref_text": "", "x_vector_only": False},
            {"id": "warm_host", "name": t("qwen3_tts.profile_warm_host", "Warm Host"), "mode": "custom_voice", "speaker": "Serena", "instruct": TONE_PRESETS["warm"], "ref_audio": "", "ref_text": "", "x_vector_only": False},
            {"id": "voice_design", "name": t("qwen3_tts.profile_voice_design", "Designed Voice"), "mode": "voice_design", "speaker": "Vivian", "instruct": t("qwen3_tts.voice_design_default", "A clear, modern Korean female voice in her late twenties with soft warmth, clean diction, and steady confidence."), "ref_audio": "", "ref_text": "", "x_vector_only": False},
        ]

    def _load_profiles(self):
        if PROFILE_FILE.exists():
            try:
                data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
                if data:
                    return data
            except Exception:
                pass
        profiles = self._default_profiles()
        self._save_profiles(profiles)
        return profiles

    def _save_profiles(self, profiles=None):
        PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_FILE.write_text(json.dumps(profiles or self.profiles, ensure_ascii=False, indent=2), encoding="utf-8")

    def _profile_names(self):
        return [p["name"] for p in self.profiles]

    def _profile_by_name(self, name):
        return next((p for p in self.profiles if p["name"] == name), self.profiles[0])

    def _refresh_profiles(self):
        names = self._profile_names()
        if self.profile_var.get() not in names:
            self.profile_var.set(names[0])
        if hasattr(self, "profile_menu"):
            self.profile_menu.configure(values=names)
        if hasattr(self, "profile_card_list"):
            self._refresh_profile_panel_cards()
        self._render_messages()

    def _message_by_id(self, message_id):
        return next(m for m in self.messages if m["id"] == message_id)

    def _toggle_action_menu(self, message_id):
        self.expanded_actions_message_id = None if self.expanded_actions_message_id == message_id else message_id
        self._render_messages()

    def _toggle_text_editor(self, message_id):
        self.expanded_text_editor_message_id = None if self.expanded_text_editor_message_id == message_id else message_id
        self._render_messages()

    def _clone_quality_status(self, profile):
        if profile.get("mode") != "voice_clone":
            return None
        ref_audio = profile.get("ref_audio", "").strip()
        ref_text = profile.get("ref_text", "").strip()
        if not ref_audio:
            return ("missing", t("qwen3_tts.clone_quality_missing", "Missing reference audio"))
        audio_path = Path(ref_audio)
        if not audio_path.exists():
            return ("missing", t("qwen3_tts.clone_quality_missing_file", "Reference file not found"))
        duration = 0.0
        try:
            with wave.open(str(audio_path), "rb") as wav_file:
                duration = wav_file.getnframes() / max(1, wav_file.getframerate())
        except Exception:
            return ("warning", t("qwen3_tts.clone_quality_unknown", "Reference loaded, duration unknown"))
        if duration < 2.5:
            return ("warning", t("qwen3_tts.clone_quality_short", "Reference is short"))
        if not ref_text:
            return ("warning", t("qwen3_tts.clone_quality_no_transcript", "Transcript missing"))
        return ("good", t("qwen3_tts.clone_quality_good", "Reference ready"))

    def _waveform_points(self, path, columns=56):
        try:
            with wave.open(str(path), "rb") as wav_file:
                channels = wav_file.getnchannels()
                frames = wav_file.getnframes()
                if frames <= 0:
                    return [0.12] * columns
                raw = wav_file.readframes(min(frames, 240000))
            samples = array("h")
            samples.frombytes(raw)
            if not samples:
                return [0.12] * columns
            stride = max(1, len(samples) // columns)
            points = []
            for idx in range(0, len(samples), stride):
                chunk = samples[idx : idx + stride]
                if not chunk:
                    continue
                values = chunk[::channels] if channels > 1 else chunk
                peak = max(abs(v) for v in values) / 32767.0
                points.append(max(0.08, min(1.0, peak)))
                if len(points) >= columns:
                    break
            return points or [0.12] * columns
        except Exception:
            return [0.12] * columns

    def _draw_waveform(self, parent, path):
        canvas = tk.Canvas(parent, width=420, height=58, bg="#111111", highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="x", expand=True, padx=(0, 14))
        points = self._waveform_points(path)
        self._render_waveform_canvas(canvas, points, 0.0)
        return canvas, points

    def _render_waveform_canvas(self, canvas, points, progress_ratio):
        canvas.delete("all")
        width = 420
        height = 58
        mid = height / 2
        bar_w = max(4, width / max(len(points), 1))
        active_index = int(len(points) * max(0.0, min(1.0, progress_ratio)))
        for idx, value in enumerate(points):
            x0 = idx * bar_w + 1
            x1 = x0 + max(2, bar_w - 2)
            amp = max(4, value * (height * 0.4))
            if idx <= active_index:
                color = "#78B9FF" if idx % 2 == 0 else "#9FD2FF"
            else:
                color = "#1E3A5F" if idx % 2 == 0 else "#284A73"
            canvas.create_rectangle(x0, mid - amp, x1, mid + amp, fill=color, outline="")
        playhead_x = max(0, min(width, width * max(0.0, min(1.0, progress_ratio))))
        canvas.create_line(playhead_x, 6, playhead_x, height - 6, fill="#D8EEFF", width=2)
        canvas.create_oval(playhead_x - 4, mid - 4, playhead_x + 4, mid + 4, fill="#D8EEFF", outline="")

    def _output_summary(self, path):
        try:
            with wave.open(str(path), "rb") as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / sample_rate if sample_rate else 0
            return t("qwen3_tts.output_summary", "{seconds:.1f}s · WAV").format(seconds=duration)
        except Exception:
            return t("qwen3_tts.output_summary_unknown", "WAV result")

    def _format_time(self, seconds):
        seconds = max(0, int(seconds))
        return f"{seconds // 60}:{seconds % 60:02d}"

    def _register_waveform_view(self, path, canvas, points, duration, time_var):
        self.waveform_views[path] = {
            "canvas": canvas,
            "points": points,
            "duration": duration,
            "time_var": time_var,
        }

    def _update_waveform_views(self):
        for path, view in list(self.waveform_views.items()):
            ratio = 0.0
            label = self._format_time(view["duration"])
            if self.current_playback_path == path and self.current_playback_started_at is not None and view["duration"] > 0:
                elapsed = max(0.0, time.monotonic() - self.current_playback_started_at)
                ratio = min(1.0, elapsed / view["duration"])
                label = f"{self._format_time(elapsed)} / {self._format_time(view['duration'])}"
            self._render_waveform_canvas(view["canvas"], view["points"], ratio)
            view["time_var"].set(label)

    def _schedule_playback_tick(self):
        if self.playback_after_id:
            self.after_cancel(self.playback_after_id)
        self.playback_after_id = self.after(160, self._tick_playback)

    def _tick_playback(self):
        if not self.current_playback_path or self.current_playback_started_at is None:
            self.playback_after_id = None
            self._update_waveform_views()
            return
        elapsed = time.monotonic() - self.current_playback_started_at
        if elapsed >= self.current_playback_duration:
            self._stop_playback(redraw=False)
            self._update_waveform_views()
            self._render_messages()
            return
        self._update_waveform_views()
        self.playback_after_id = self.after(160, self._tick_playback)

    def _build_ui(self):
        self.title_label.configure(text=f"Qwen3-TTS · 1.7B")
        top = ctk.CTkFrame(self.main_frame, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER, height=74)
        top.pack(fill="x", padx=18, pady=(10, 8))
        top.pack_propagate(False)
        self.model_status = ctk.CTkLabel(top, text="", text_color=THEME_TEXT_MAIN, font=ctk.CTkFont(size=15, weight="bold"))
        self.model_status.pack(anchor="w", padx=16, pady=(12, 2))
        self.model_hint = ctk.CTkLabel(top, text="", text_color=THEME_TEXT_DIM)
        self.model_hint.pack(anchor="w", padx=16)

        self.content_row = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_row.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        self.chat_frame = ctk.CTkScrollableFrame(self.content_row, fg_color="transparent")
        self.chat_frame.pack(side="left", fill="both", expand=True)
        self.profile_panel = ctk.CTkFrame(self.content_row, fg_color="#0E1420", corner_radius=22, border_width=1, border_color=THEME_BORDER, width=300)
        self.profile_panel.pack_propagate(False)
        self._build_profile_panel()

        composer = ctk.CTkFrame(self.footer_frame, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER, corner_radius=22)
        composer.pack(fill="x", padx=18, pady=(10, 12))
        top_row = ctk.CTkFrame(composer, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(12, 8))
        ctk.CTkLabel(top_row, text=t("qwen3_tts.input_profile", "Profile"), text_color=THEME_TEXT_DIM).pack(side="left", padx=(0, 6))
        self.profile_menu = ctk.CTkOptionMenu(top_row, variable=self.profile_var, values=self._profile_names(), fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, width=160)
        self.profile_menu.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(top_row, text=t("qwen3_tts.input_tone", "Tone"), text_color=THEME_TEXT_DIM).pack(side="left", padx=(0, 6))
        ctk.CTkOptionMenu(top_row, variable=self.tone_var, values=list(TONE_PRESETS.keys()), fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, width=130).pack(side="left", padx=(0, 10))
        ctk.CTkButton(top_row, text=t("qwen3_tts.profile_manage", "Profiles"), width=90, command=self._open_profile_editor).pack(side="left", padx=(0, 8))
        self.advanced_btn = ctk.CTkButton(top_row, text=t("qwen3_tts.advanced_show", "More"), width=80, command=self._toggle_advanced)
        self.advanced_btn.pack(side="left", padx=(0, 8))
        self.output_btn = ctk.CTkButton(top_row, text=t("qwen3_tts.open_folder", "Open Folder"), width=100, command=self._open_output_folder)
        self.output_btn.pack(side="right")

        self.advanced_frame = ctk.CTkFrame(composer, fg_color="transparent")
        adv_row = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        adv_row.pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkLabel(adv_row, text=t("qwen3_tts.input_language", "Language"), text_color=THEME_TEXT_DIM).pack(side="left", padx=(0, 6))
        ctk.CTkOptionMenu(adv_row, variable=self.language_var, values=SUPPORTED_LANGUAGES, fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, width=140).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(adv_row, text=t("qwen3_tts.input_device", "Device"), text_color=THEME_TEXT_DIM).pack(side="left", padx=(0, 6))
        ctk.CTkOptionMenu(adv_row, variable=self.device_var, values=["cuda", "auto", "cpu"], fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, width=110).pack(side="left", padx=(0, 10))
        ctk.CTkButton(adv_row, text=t("qwen3_tts.clone_setup", "Clone Setup"), width=100, command=self._open_profile_editor).pack(side="left")

        self.input_box = ctk.CTkTextbox(composer, height=88)
        self.input_box.pack(fill="x", padx=14, pady=(0, 10))
        self.input_box.insert("1.0", t("qwen3_tts.sample_short_text", "Hello from ContextHub. This is a quick voice test."))

        bottom_row = ctk.CTkFrame(composer, fg_color="transparent")
        bottom_row.pack(fill="x", padx=14, pady=(0, 12))
        self.selected_label = ctk.CTkLabel(bottom_row, text=t("qwen3_tts.selection_none", "No bubble selected. New text will be added at the bottom."), text_color=THEME_TEXT_DIM)
        self.selected_label.pack(side="left")
        ctk.CTkButton(bottom_row, text=t("qwen3_tts.add_bubble", "Add Bubble"), width=90, command=self._add_or_update_message).pack(side="right", padx=(8, 0))
        self.generate_btn = ctk.CTkButton(bottom_row, text=t("qwen3_tts.generate_dialogue", "Generate Conversation"), width=170, command=self._generate_all, fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER)
        self.generate_btn.pack(side="right")

        self.status_label = ctk.CTkLabel(self.footer_frame, textvariable=self.status_var, anchor="w")
        self.status_label.pack(fill="x", padx=20, pady=(0, 6))

        self.overlay = ctk.CTkFrame(self.outer_frame, fg_color="#080808", corner_radius=16, border_width=1, border_color=THEME_ACCENT)
        self.overlay.place_forget()
        self.overlay_label = ctk.CTkLabel(self.overlay, text=t("qwen3_tts.overlay_wait", "Preparing generation..."), font=ctk.CTkFont(size=18, weight="bold"))
        self.overlay_label.pack(pady=(28, 10))
        self.overlay_hint = ctk.CTkLabel(self.overlay, text="", text_color=THEME_TEXT_DIM)
        self.overlay_hint.pack(pady=(0, 14))
        self.overlay_progress = ctk.CTkProgressBar(self.overlay, width=320)
        self.overlay_progress.pack(pady=(0, 18))
        self.overlay_progress.set(0)
        overlay_actions = ctk.CTkFrame(self.overlay, fg_color="transparent")
        overlay_actions.pack(pady=(0, 24))
        self.overlay_cancel = ctk.CTkButton(overlay_actions, text=t("common.cancel", "Cancel"), width=100, command=self._cancel_or_close)
        self.overlay_cancel.pack(side="left", padx=(0, 8))
        self.overlay_folder = ctk.CTkButton(overlay_actions, text=t("qwen3_tts.open_folder", "Open Folder"), width=100, command=self._open_output_folder)
        self.overlay_folder.pack(side="left")

    def _build_profile_panel(self):
        header = ctk.CTkFrame(self.profile_panel, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(14, 8))
        ctk.CTkLabel(header, text=t("qwen3_tts.profile_panel_title", "Voice Profiles"), font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text=t("common.close", "Close"), width=70, command=self._close_profile_panel).pack(side="right")

        self.profile_card_list = ctk.CTkScrollableFrame(self.profile_panel, fg_color="transparent", height=220)
        self.profile_card_list.pack(fill="both", expand=False, padx=12, pady=(0, 10))

        form = ctk.CTkFrame(self.profile_panel, fg_color="#111827", corner_radius=18, border_width=1, border_color=THEME_BORDER)
        form.pack(fill="both", expand=True, padx=12, pady=(0, 14))
        self.panel_name_var = ctk.StringVar()
        self.panel_mode_var = ctk.StringVar(value="custom_voice")
        self.panel_speaker_var = ctk.StringVar(value="Vivian")
        self.panel_ref_audio_var = ctk.StringVar()
        self.panel_ref_text_var = ctk.StringVar()
        self.panel_xvec_var = ctk.BooleanVar(value=False)
        self.profile_form_target_id = None

        ctk.CTkLabel(form, text=t("qwen3_tts.profile_name", "Profile Name")).pack(anchor="w", padx=12, pady=(12, 4))
        ctk.CTkEntry(form, textvariable=self.panel_name_var).pack(fill="x", padx=12)
        ctk.CTkLabel(form, text=t("qwen3_tts.mode", "Mode"), text_color=THEME_TEXT_DIM).pack(anchor="w", padx=12, pady=(12, 4))
        self.panel_mode_menu = ctk.CTkOptionMenu(form, variable=self.panel_mode_var, values=["custom_voice", "voice_clone", "voice_design"], command=self._on_profile_mode_change)
        self.panel_mode_menu.pack(fill="x", padx=12)
        self.panel_mode_hint = ctk.CTkLabel(form, text="", text_color=THEME_TEXT_DIM, justify="left", wraplength=250)
        self.panel_mode_hint.pack(anchor="w", padx=12, pady=(8, 2))

        self.panel_speaker_section = ctk.CTkFrame(form, fg_color="transparent")
        ctk.CTkLabel(self.panel_speaker_section, text=t("qwen3_tts.speaker", "Speaker"), text_color=THEME_TEXT_DIM).pack(anchor="w", pady=(12, 4))
        self.panel_speaker_menu = ctk.CTkOptionMenu(self.panel_speaker_section, variable=self.panel_speaker_var, values=SUPPORTED_SPEAKERS)
        self.panel_speaker_menu.pack(fill="x")

        self.panel_instruct_section = ctk.CTkFrame(form, fg_color="transparent")
        ctk.CTkLabel(self.panel_instruct_section, text=t("qwen3_tts.instruct", "Style Instruction"), text_color=THEME_TEXT_DIM).pack(anchor="w", pady=(12, 4))
        self.panel_instruct_box = ctk.CTkTextbox(self.panel_instruct_section, height=92)
        self.panel_instruct_box.pack(fill="x")

        self.panel_clone_section = ctk.CTkFrame(form, fg_color="transparent")
        ctk.CTkLabel(self.panel_clone_section, text=t("qwen3_tts.ref_audio", "Reference Audio"), text_color=THEME_TEXT_DIM).pack(anchor="w", pady=(12, 4))
        ref_row = ctk.CTkFrame(self.panel_clone_section, fg_color="transparent")
        ref_row.pack(fill="x")
        ctk.CTkEntry(ref_row, textvariable=self.panel_ref_audio_var).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(ref_row, text=t("common.browse", "Browse"), width=78, command=lambda: self._browse_ref_audio(self.panel_ref_audio_var)).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(self.panel_clone_section, text=t("qwen3_tts.ref_text", "Reference Transcript"), text_color=THEME_TEXT_DIM).pack(anchor="w", pady=(12, 4))
        ctk.CTkEntry(self.panel_clone_section, textvariable=self.panel_ref_text_var).pack(fill="x")
        ctk.CTkCheckBox(self.panel_clone_section, text=t("qwen3_tts.x_vector_only", "Use x-vector only mode"), variable=self.panel_xvec_var).pack(anchor="w", pady=(10, 0))

        for section in [self.panel_speaker_section, self.panel_instruct_section, self.panel_clone_section]:
            section.pack(fill="x", padx=12)

        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.pack(fill="x", padx=12, pady=(14, 12))
        ctk.CTkButton(actions, text=t("qwen3_tts.save_profile", "Save"), width=88, command=self._save_profile_panel).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text=t("qwen3_tts.add_profile", "Add Profile"), width=92, command=self._start_new_profile).pack(side="left", padx=(0, 8))
        self.panel_delete_btn = ctk.CTkButton(actions, text=t("qwen3_tts.delete_profile", "Delete"), width=80, command=self._delete_profile_from_panel)
        self.panel_delete_btn.pack(side="right")
        self._on_profile_mode_change(self.panel_mode_var.get())

    def _refresh_status_bar(self):
        self.model_status.configure(text=t("qwen3_tts.status_bar", "Model 1.7B ready · Device: {device} · Profiles: {count}").format(device=self.device_var.get(), count=len(self.profiles)))
        self.model_hint.configure(text=t("qwen3_tts.status_hint", "Click a bubble to edit, regenerate, delete, or swap voice profile."))

    def _toggle_advanced(self):
        self.advanced_open = not self.advanced_open
        if self.advanced_open:
            self.advanced_frame.pack(fill="x")
            self.advanced_btn.configure(text=t("qwen3_tts.advanced_hide", "Hide"))
        else:
            self.advanced_frame.pack_forget()
            self.advanced_btn.configure(text=t("qwen3_tts.advanced_show", "More"))

    def _prefill_from_target(self):
        if self.target_path and self.target_path.exists():
            if self.target_path.suffix.lower() in {".txt", ".md"}:
                text = self.target_path.read_text(encoding="utf-8", errors="replace")
                self.input_box.delete("1.0", "end")
                self.input_box.insert("1.0", text)
            elif self.target_path.suffix.lower() in AUDIO_EXTENSIONS:
                self.profiles.append({"id": "clone_import", "name": t("qwen3_tts.profile_imported_clone", "Imported Clone"), "mode": "voice_clone", "speaker": "Vivian", "instruct": "", "ref_audio": str(self.target_path), "ref_text": "", "x_vector_only": False})
                self.profile_var.set(self.profiles[-1]["name"])
                self._save_profiles()
        if not self.messages:
            self._append_message(t("qwen3_tts.dialogue_role_narrator", "Narrator"), self.profile_var.get(), self.tone_var.get(), self.input_box.get("1.0", "end").strip())
            self._append_message(t("qwen3_tts.dialogue_role_host", "Host"), self.profiles[1]["name"], "warm", t("qwen3_tts.dialogue_sample_reply", "This second line shows how another profile can answer in the same batch."))

    def _append_message(self, role, profile_name, tone_key, text):
        self.messages.append({"id": f"msg_{len(self.messages)+1}", "role": role, "profile": profile_name, "tone": tone_key, "text": text, "status": "ready", "output": ""})

    def _add_or_update_message(self):
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning(t("common.warning", "Warning"), t("qwen3_tts.text_required", "Text is required."))
            return
        if self.selected_message_id:
            msg = next(m for m in self.messages if m["id"] == self.selected_message_id)
            msg.update({"profile": self.profile_var.get(), "tone": self.tone_var.get(), "text": text})
        else:
            self._append_message(self.profile_var.get(), self.profile_var.get(), self.tone_var.get(), text)
        self._clear_selection()
        self._render_messages()

    def _render_messages(self):
        self.waveform_views = {}
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        for msg in self.messages:
            row = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
            row.pack(fill="x", pady=(0, 10), padx=4)
            avatar = ctk.CTkFrame(row, width=42, height=42, corner_radius=21, fg_color=self._profile_color(msg["profile"]))
            avatar.pack(side="left", padx=(0, 10), pady=(8, 0))
            avatar.pack_propagate(False)
            ctk.CTkLabel(avatar, text=(msg["role"][:1] or "?").upper(), font=ctk.CTkFont(weight="bold")).pack(expand=True)
            bubble = ctk.CTkFrame(row, fg_color=THEME_CARD, border_width=1, border_color=THEME_ACCENT if msg["id"] == self.selected_message_id else THEME_BORDER, corner_radius=24)
            bubble.pack(side="left", fill="x", expand=True)
            head = ctk.CTkFrame(bubble, fg_color="transparent")
            head.pack(fill="x", padx=16, pady=(12, 4))
            ctk.CTkLabel(head, text=msg["role"], font=ctk.CTkFont(weight="bold")).pack(side="left")
            meta = ctk.CTkFrame(head, fg_color="transparent")
            meta.pack(side="right")
            profile_mode = self._profile_by_name(msg["profile"]).get("mode", "custom_voice")
            mode_badge = ctk.CTkFrame(meta, fg_color=self._profile_color(msg["profile"]), corner_radius=999)
            mode_badge.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(mode_badge, text=self._profile_mode_label(profile_mode), font=ctk.CTkFont(size=11, weight="bold")).pack(padx=10, pady=2)
            ctk.CTkLabel(meta, text=msg["profile"], text_color=THEME_TEXT_DIM).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(meta, text=msg["tone"], text_color=THEME_TEXT_DIM).pack(side="left", padx=(0, 8))
            badge = ctk.CTkFrame(meta, fg_color=STATUS_COLORS.get(msg["status"], THEME_TEXT_DIM), corner_radius=999)
            badge.pack(side="left")
            ctk.CTkLabel(badge, text=self._status_label(msg["status"]), font=ctk.CTkFont(size=11, weight="bold")).pack(padx=10, pady=2)
            ctk.CTkLabel(bubble, text=msg["text"], justify="left", wraplength=700).pack(anchor="w", padx=16, pady=(0, 12))
            for widget in [row, avatar, bubble, *bubble.winfo_children()]:
                widget.bind("<Button-1>", lambda _e, mid=msg["id"]: self._select_message(mid))
            if msg["id"] == self.selected_message_id:
                tray = ctk.CTkFrame(bubble, fg_color="#10151F", corner_radius=20, border_width=1, border_color=THEME_ACCENT)
                tray.pack(fill="x", padx=16, pady=(0, 12))
                tray_header = ctk.CTkFrame(tray, fg_color="transparent")
                tray_header.pack(fill="x", padx=14, pady=(12, 6))
                ctk.CTkLabel(tray_header, text=t("qwen3_tts.detail_tray_title", "Voice Detail"), font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
                ctk.CTkLabel(tray_header, text=t("qwen3_tts.detail_tray_hint", "Adjust this line before generating."), text_color=THEME_TEXT_DIM).pack(side="right")
                profile = self._profile_by_name(msg["profile"])
                if profile.get("mode") == "voice_clone":
                    quality = self._clone_quality_status(profile)
                    if quality:
                        _, quality_text = quality
                        quality_row = ctk.CTkFrame(tray, fg_color="transparent")
                        quality_row.pack(fill="x", padx=14, pady=(0, 8))
                        ctk.CTkLabel(quality_row, text=f"{t('qwen3_tts.clone_quality_label', 'Clone Status')}: {quality_text}", text_color=THEME_TEXT_DIM).pack(side="left")
                inline_editor = ctk.CTkFrame(tray, fg_color="transparent")
                inline_editor.pack(fill="x", padx=14, pady=(0, 10))
                ctk.CTkLabel(inline_editor, text=t("qwen3_tts.input_profile", "Profile"), text_color=THEME_TEXT_DIM).pack(side="left", padx=(0, 6))
                profile_var = ctk.StringVar(value=msg["profile"])
                ctk.CTkOptionMenu(
                    inline_editor,
                    variable=profile_var,
                    values=self._profile_names(),
                    width=160,
                    fg_color=THEME_DROPDOWN_FG,
                    button_color=THEME_DROPDOWN_BTN,
                    button_hover_color=THEME_DROPDOWN_HOVER,
                    command=lambda value, mid=msg["id"]: self._update_message_profile(mid, value),
                ).pack(side="left", padx=(0, 10))
                ctk.CTkLabel(inline_editor, text=t("qwen3_tts.input_tone", "Tone"), text_color=THEME_TEXT_DIM).pack(side="left", padx=(0, 6))
                tone_var = ctk.StringVar(value=msg["tone"])
                ctk.CTkOptionMenu(
                    inline_editor,
                    variable=tone_var,
                    values=list(TONE_PRESETS.keys()),
                    width=130,
                    fg_color=THEME_DROPDOWN_FG,
                    button_color=THEME_DROPDOWN_BTN,
                    button_hover_color=THEME_DROPDOWN_HOVER,
                    command=lambda value, mid=msg["id"]: self._update_message_tone(mid, value),
                ).pack(side="left", padx=(0, 10))
                ctk.CTkButton(inline_editor, text=t("qwen3_tts.profile_edit", "Edit"), width=70, command=lambda name=msg["profile"]: self._open_profile_editor(name)).pack(side="left")
                text_tools = ctk.CTkFrame(tray, fg_color="transparent")
                text_tools.pack(fill="x", padx=14, pady=(0, 10))
                ctk.CTkLabel(text_tools, text=t("qwen3_tts.text_quick_edit", "Text"), text_color=THEME_TEXT_DIM).pack(side="left")
                ctk.CTkButton(text_tools, text=t("qwen3_tts.text_edit_toggle", "Edit Text"), width=90, command=lambda mid=msg["id"]: self._toggle_text_editor(mid)).pack(side="right")
                if self.expanded_text_editor_message_id == msg["id"]:
                    editor_card = ctk.CTkFrame(tray, fg_color="#0B1220", corner_radius=16, border_width=1, border_color=THEME_BORDER)
                    editor_card.pack(fill="x", padx=14, pady=(0, 12))
                    text_box = ctk.CTkTextbox(editor_card, height=110)
                    text_box.pack(fill="x", padx=12, pady=(12, 8))
                    text_box.insert("1.0", msg["text"])
                    edit_actions = ctk.CTkFrame(editor_card, fg_color="transparent")
                    edit_actions.pack(fill="x", padx=12, pady=(0, 12))
                    ctk.CTkButton(edit_actions, text=t("qwen3_tts.text_apply", "Apply Text"), width=90, command=lambda mid=msg["id"], box=text_box: self._apply_message_text(mid, box)).pack(side="left", padx=(0, 8))
                    ctk.CTkButton(edit_actions, text=t("qwen3_tts.text_cancel", "Cancel"), width=80, command=lambda mid=msg["id"]: self._toggle_text_editor(mid)).pack(side="left")
                actions = ctk.CTkFrame(tray, fg_color="transparent")
                actions.pack(fill="x", padx=14, pady=(0, 14))
                ctk.CTkButton(actions, text=t("qwen3_tts.generate_one", "Generate This"), width=120, command=lambda mid=msg["id"]: self._generate_one(mid), fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER).pack(side="left", padx=(0, 8))
                ctk.CTkButton(actions, text=t("qwen3_tts.more_actions", "More"), width=92, command=lambda mid=msg["id"]: self._toggle_action_menu(mid)).pack(side="left")
                if self.expanded_actions_message_id == msg["id"]:
                    more_panel = ctk.CTkFrame(tray, fg_color="#0B1220", corner_radius=16, border_width=1, border_color=THEME_BORDER)
                    more_panel.pack(fill="x", padx=14, pady=(0, 12))
                    ctk.CTkLabel(more_panel, text=t("qwen3_tts.more_actions_hint", "Secondary actions for this line."), text_color=THEME_TEXT_DIM).pack(anchor="w", padx=12, pady=(10, 8))
                    more_row = ctk.CTkFrame(more_panel, fg_color="transparent")
                    more_row.pack(fill="x", padx=12, pady=(0, 12))
                    ctk.CTkButton(more_row, text=t("qwen3_tts.use_composer", "Use Composer Settings"), width=160, command=lambda mid=msg["id"]: self._apply_current_profile(mid)).pack(side="left", padx=(0, 8))
                    ctk.CTkButton(more_row, text=t("qwen3_tts.delete_bubble", "Delete"), width=80, command=lambda mid=msg["id"]: self._delete_message(mid)).pack(side="left")
                if msg["output"]:
                    result_card = ctk.CTkFrame(tray, fg_color="#0E1726", corner_radius=18, border_width=1, border_color=THEME_BORDER)
                    result_card.pack(fill="x", padx=14, pady=(0, 14))
                    result_head = ctk.CTkFrame(result_card, fg_color="transparent")
                    result_head.pack(fill="x", padx=14, pady=(12, 8))
                    ctk.CTkLabel(result_head, text=t("qwen3_tts.result_card_title", "Generated Result"), font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
                    ctk.CTkLabel(result_head, text=self._output_summary(msg["output"]), text_color=THEME_TEXT_DIM).pack(side="right")
                    info_row = ctk.CTkFrame(result_card, fg_color="transparent")
                    info_row.pack(fill="x", padx=14, pady=(0, 8))
                    mode_text = self._profile_mode_label(profile.get("mode", "custom_voice"))
                    ctk.CTkLabel(info_row, text=f"{t('qwen3_tts.result_voice_type', 'Type')}: {mode_text}", text_color=THEME_TEXT_DIM).pack(side="left", padx=(0, 12))
                    if profile.get("mode") == "voice_clone":
                        ref_name = Path(profile.get("ref_audio", "")).name if profile.get("ref_audio") else t("qwen3_tts.reference_missing", "missing")
                        ctk.CTkLabel(info_row, text=f"{t('qwen3_tts.result_reference', 'Reference')}: {ref_name}", text_color=THEME_TEXT_DIM).pack(side="left")
                        quality = self._clone_quality_status(profile)
                        if quality:
                            _, quality_text = quality
                            ctk.CTkLabel(info_row, text=f"{t('qwen3_tts.clone_quality_label', 'Clone Status')}: {quality_text}", text_color=THEME_TEXT_DIM).pack(side="left", padx=(12, 0))
                    wave_row = ctk.CTkFrame(result_card, fg_color="transparent")
                    wave_row.pack(fill="x", padx=14, pady=(0, 10))
                    canvas, points = self._draw_waveform(wave_row, msg["output"])
                    duration = 0.0
                    try:
                        with wave.open(str(msg["output"]), "rb") as wav_file:
                            duration = wav_file.getnframes() / max(1, wav_file.getframerate())
                    except Exception:
                        pass
                    side = ctk.CTkFrame(wave_row, fg_color="transparent")
                    side.pack(side="right")
                    play_label = t("qwen3_tts.stop_result", "Stop") if self.current_playback_path == msg["output"] else t("qwen3_tts.play_result", "Play Result")
                    play_btn = ctk.CTkButton(side, text=play_label, width=100, command=lambda path=msg["output"]: self._toggle_playback(path))
                    play_btn.pack(side="right")
                    time_var = ctk.StringVar(value=self._format_time(duration))
                    ctk.CTkLabel(side, textvariable=time_var, text_color=THEME_TEXT_DIM).pack(side="right", padx=(0, 10))
                    self._register_waveform_view(msg["output"], canvas, points, duration, time_var)
                    result_actions = ctk.CTkFrame(result_card, fg_color="transparent")
                    result_actions.pack(fill="x", padx=14, pady=(0, 12))
                    ctk.CTkButton(result_actions, text=t("qwen3_tts.open_result", "Reveal File"), width=100, command=lambda path=msg["output"]: self._reveal_output(path)).pack(side="left", padx=(0, 8))
                    ctk.CTkButton(result_actions, text=t("qwen3_tts.regenerate_result", "Regenerate"), width=100, command=lambda mid=msg["id"]: self._generate_one(mid)).pack(side="left")
        self._update_waveform_views()

    def _select_message(self, message_id):
        self.selected_message_id = message_id
        msg = next(m for m in self.messages if m["id"] == message_id)
        self.profile_var.set(msg["profile"])
        self.tone_var.set(msg["tone"])
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", msg["text"])
        self.selected_label.configure(text=t("qwen3_tts.selection_active", "Selected bubble: click Add Bubble to update it."))
        self._render_messages()

    def _clear_selection(self):
        self.selected_message_id = None
        self.selected_label.configure(text=t("qwen3_tts.selection_none", "No bubble selected. New text will be added at the bottom."))
        self.input_box.delete("1.0", "end")

    def _delete_message(self, message_id):
        self.messages = [m for m in self.messages if m["id"] != message_id]
        self._clear_selection()
        self._render_messages()

    def _apply_current_profile(self, message_id):
        msg = self._message_by_id(message_id)
        msg["profile"] = self.profile_var.get()
        msg["tone"] = self.tone_var.get()
        self._render_messages()

    def _update_message_profile(self, message_id, profile_name):
        msg = self._message_by_id(message_id)
        msg["profile"] = profile_name
        self.profile_var.set(profile_name)
        self._render_messages()

    def _update_message_tone(self, message_id, tone_name):
        msg = self._message_by_id(message_id)
        msg["tone"] = tone_name
        self.tone_var.set(tone_name)
        self._render_messages()

    def _apply_message_text(self, message_id, text_box):
        text = text_box.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning(t("common.warning", "Warning"), t("qwen3_tts.text_required", "Text is required."))
            return
        msg = self._message_by_id(message_id)
        msg["text"] = text
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", text)
        self.expanded_text_editor_message_id = None
        self._render_messages()

    def _compose_job(self, msg):
        profile = self._profile_by_name(msg["profile"])
        if profile["mode"] == "voice_clone" and not profile["ref_audio"]:
            raise ValueError(t("qwen3_tts.clone_profile_missing_audio", "Voice Clone profiles need a reference audio file."))
        if profile["mode"] == "voice_design" and not (profile.get("instruct") or "").strip():
            raise ValueError(t("qwen3_tts.design_profile_missing_prompt", "Voice Design profiles need a voice description."))
        instruct = profile["instruct"]
        if profile["mode"] != "voice_clone" and msg["tone"] in TONE_PRESETS:
            instruct = f"{instruct}\n{TONE_PRESETS[msg['tone']]}".strip()
        return {"mode": profile["mode"], "size": "1.7B", "device": self.device_var.get(), "text": msg["text"], "language": self.language_var.get(), "speaker": profile["speaker"], "instruct": instruct, "ref_audio": profile["ref_audio"], "ref_text": profile["ref_text"], "x_vector_only": bool(profile["x_vector_only"])}

    def _generate_one(self, message_id):
        msg = next(m for m in self.messages if m["id"] == message_id)
        self._run_jobs([msg], single_target=msg)

    def _generate_all(self):
        if not self.messages:
            messagebox.showwarning(t("common.warning", "Warning"), t("qwen3_tts.dialogue_empty", "Add at least one dialogue line."))
            return
        self._run_jobs(self.messages)

    def _run_jobs(self, message_items, single_target=None):
        try:
            jobs = []
            targets = []
            for index, msg in enumerate(message_items, start=1):
                if not msg["text"].strip():
                    continue
                targets.append(msg)
                job = self._compose_job(msg)
                job["file_name"] = f"{index:03d}_{msg['role'].lower().replace(' ', '_')}.wav"
                jobs.append(job)
            if not jobs:
                raise ValueError(t("qwen3_tts.dialogue_empty", "Add at least one dialogue line."))
        except Exception as exc:
            messagebox.showwarning(t("common.warning", "Warning"), str(exc))
            return

        out_dir = self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as tmp:
            json.dump({"jobs": jobs}, tmp, ensure_ascii=False, indent=2)
            self.pending_jobs_file = tmp.name
        for msg in targets:
            msg["status"] = "queued"
        self.total_jobs = len(targets)
        self.completed_jobs = 0
        self._render_messages()
        self._show_overlay(t("qwen3_tts.overlay_wait", "Preparing generation..."), f"0 / {len(targets)}")
        args = [str(Path(__file__).with_name("qwen3_tts.py")), "--size", "1.7B", "--device", self.device_var.get(), "--jobs-file", self.pending_jobs_file, "--output-dir", str(out_dir)]
        self.generate_btn.configure(state="disabled")

        def run():
            try:
                self.current_process = start_ai_script(*args)
                lines = []
                if self.current_process.stdout:
                    for raw in self.current_process.stdout:
                        line = raw.rstrip()
                        lines.append(line)
                        self.after(0, lambda l=line: self._append_runtime_log(l))
                        if "[INFO] Generating job " in line:
                            try:
                                progress_text = line.split("Generating job ", 1)[1].split(":", 1)[0]
                                current, total = progress_text.split("/")
                                self.after(0, lambda c=int(current), t=int(total): self._update_overlay_progress(c, t))
                            except Exception:
                                pass
                self.current_process.wait()
                stdout = "\n".join(lines)
                payload = self._extract_payload(stdout or "")
                ok = self.current_process.returncode == 0
                self.current_process = None
                self.after(0, lambda: self._finish_generation(ok, payload, targets, stdout or "Unknown error"))
            except Exception as exc:
                self.current_process = None
                self.after(0, lambda: self._finish_generation(False, None, targets, str(exc)))
            finally:
                if self.pending_jobs_file:
                    try:
                        Path(self.pending_jobs_file).unlink(missing_ok=True)
                    except Exception:
                        pass
                    self.pending_jobs_file = None

        threading.Thread(target=run, daemon=True).start()

    def _extract_payload(self, stdout):
        payload = None
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    payload = json.loads(line)
                except Exception:
                    pass
        return payload

    def _append_runtime_log(self, line):
        if line:
            self.status_var.set(line[:120])

    def _update_overlay_progress(self, current, total):
        self.completed_jobs = current
        self.total_jobs = total
        self.overlay_hint.configure(text=f"{current} / {total}")
        self.overlay_progress.set(0 if total <= 0 else current / total)

    def _finish_generation(self, ok, payload, targets, error_message):
        self.generate_btn.configure(state="normal")
        if not ok:
            for msg in targets:
                msg["status"] = "error"
            self.status_var.set(t("common.error", "Error"))
            self._hide_overlay()
            self._render_messages()
            messagebox.showerror(t("common.error", "Error"), error_message)
            return
        outputs = payload.get("outputs", []) if payload else []
        for idx, msg in enumerate(targets):
            msg["status"] = "done"
            if idx < len(outputs):
                msg["output"] = outputs[idx]["output"]
        self.latest_outputs = [m["output"] for m in targets if m["output"]]
        self.status_var.set(t("qwen3_tts.status_done", "Speech generated successfully."))
        self._show_overlay(t("qwen3_tts.overlay_done", "Generation complete"), f"{len(targets)} / {len(targets)}", done=True)
        self._render_messages()

    def _show_overlay(self, title, hint, done=False):
        self.overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.overlay.lift()
        self.overlay_label.configure(text=title)
        self.overlay_hint.configure(text=hint)
        self.overlay_progress.set(1.0 if done else 0.2)
        self.overlay_cancel.configure(state="disabled" if done else "normal")
        self.overlay_folder.configure(state="normal" if done else "disabled")

    def _hide_overlay(self):
        self.overlay.place_forget()

    def _open_output_folder(self):
        if os.name == "nt":
            os.startfile(str(self.output_dir))

    def _play_output(self, path):
        if path and Path(path).exists() and os.name == "nt":
            os.startfile(path)

    def _toggle_playback(self, path):
        if not path or not Path(path).exists():
            return
        if self.current_playback_path == path:
            self._stop_playback()
        else:
            winsound.PlaySound(path, winsound.SND_ASYNC | winsound.SND_FILENAME)
            self.current_playback_path = path
            self.current_playback_started_at = time.monotonic()
            try:
                with wave.open(str(path), "rb") as wav_file:
                    self.current_playback_duration = wav_file.getnframes() / max(1, wav_file.getframerate())
            except Exception:
                self.current_playback_duration = 0.0
            self._schedule_playback_tick()
            self._update_waveform_views()
        self._render_messages()

    def _stop_playback(self, redraw=True):
        winsound.PlaySound(None, winsound.SND_PURGE)
        self.current_playback_path = None
        self.current_playback_started_at = None
        self.current_playback_duration = 0.0
        if self.playback_after_id:
            self.after_cancel(self.playback_after_id)
            self.playback_after_id = None
        self._update_waveform_views()
        if redraw:
            self._render_messages()

    def _reveal_output(self, path):
        if not path or not Path(path).exists() or os.name != "nt":
            return
        os.startfile(str(Path(path).parent))

    def _play_last(self):
        if self.latest_outputs:
            self._play_output(self.latest_outputs[-1])

    def _open_profile_editor(self, focus_profile_name=None):
        self.profile_panel_visible = True
        self.profile_panel.pack(side="right", fill="y", padx=(12, 0))
        self._refresh_profile_panel_cards()
        if focus_profile_name:
            self._load_profile_into_panel(self._profile_by_name(focus_profile_name))
        elif self.profile_form_target_id is None and self.profiles:
            self._load_profile_into_panel(self.profiles[0])

    def _close_profile_panel(self):
        self.profile_panel_visible = False
        self.profile_panel.pack_forget()

    def _on_profile_mode_change(self, mode):
        hints = {
            "custom_voice": t("qwen3_tts.mode_hint_custom", "Fastest path. Pick a built-in speaker and shape the delivery with instruction."),
            "voice_clone": t("qwen3_tts.mode_hint_clone", "Best for matching a real voice. Add a clean reference clip and matching transcript."),
            "voice_design": t("qwen3_tts.mode_hint_design", "Describe a new voice character in natural language and let Qwen design it."),
        }
        self.panel_mode_hint.configure(text=hints.get(mode, ""))
        if mode == "custom_voice":
            self.panel_speaker_section.pack(fill="x", padx=12)
            self.panel_instruct_section.pack(fill="x", padx=12)
            self.panel_clone_section.pack_forget()
        elif mode == "voice_clone":
            self.panel_speaker_section.pack_forget()
            self.panel_instruct_section.pack_forget()
            self.panel_clone_section.pack(fill="x", padx=12)
        else:
            self.panel_speaker_section.pack_forget()
            self.panel_instruct_section.pack(fill="x", padx=12)
            self.panel_clone_section.pack_forget()

    def _refresh_profile_panel_cards(self):
        for widget in self.profile_card_list.winfo_children():
            widget.destroy()
        for profile in self.profiles:
            card = ctk.CTkFrame(
                self.profile_card_list,
                fg_color=THEME_CARD,
                border_width=1,
                border_color=THEME_ACCENT if profile["id"] == self.profile_form_target_id else THEME_BORDER,
                corner_radius=16,
            )
            card.pack(fill="x", pady=(0, 8))
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(10, 4))
            dot = ctk.CTkFrame(top, width=14, height=14, corner_radius=7, fg_color=self._profile_color(profile["name"]))
            dot.pack(side="left", padx=(0, 8))
            dot.pack_propagate(False)
            ctk.CTkLabel(top, text=profile["name"], font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(top, text=self._profile_mode_label(profile["mode"]), text_color=THEME_TEXT_DIM).pack(side="right")
            ctk.CTkLabel(card, text=profile.get("instruct", "")[:90] or profile.get("ref_audio", ""), justify="left", wraplength=240, text_color=THEME_TEXT_DIM).pack(anchor="w", padx=10, pady=(0, 10))
            quality = self._clone_quality_status(profile)
            if quality:
                level, quality_text = quality
                color_map = {"good": "#10B981", "warning": "#F59E0B", "missing": "#EF4444"}
                quality_row = ctk.CTkFrame(card, fg_color="transparent")
                quality_row.pack(fill="x", padx=10, pady=(0, 10))
                badge = ctk.CTkFrame(quality_row, fg_color=color_map.get(level, THEME_TEXT_DIM), corner_radius=999)
                badge.pack(side="left")
                ctk.CTkLabel(badge, text=quality_text, font=ctk.CTkFont(size=11, weight="bold")).pack(padx=8, pady=2)
            for widget in [card, top, dot, *card.winfo_children()]:
                widget.bind("<Button-1>", lambda _e, p=profile: self._load_profile_into_panel(p))
        self.panel_delete_btn.configure(state="normal" if len(self.profiles) > 1 and self.profile_form_target_id else "disabled")

    def _load_profile_into_panel(self, profile):
        self.profile_form_target_id = profile["id"]
        self.panel_name_var.set(profile["name"])
        self.panel_mode_var.set(profile["mode"])
        self.panel_speaker_var.set(profile["speaker"])
        self.panel_ref_audio_var.set(profile.get("ref_audio", ""))
        self.panel_ref_text_var.set(profile.get("ref_text", ""))
        self.panel_xvec_var.set(bool(profile.get("x_vector_only", False)))
        self.panel_instruct_box.delete("1.0", "end")
        self.panel_instruct_box.insert("1.0", profile.get("instruct", ""))
        self._on_profile_mode_change(profile["mode"])
        self._refresh_profile_panel_cards()

    def _start_new_profile(self):
        self.profile_form_target_id = None
        self.panel_name_var.set("")
        self.panel_mode_var.set("custom_voice")
        self.panel_speaker_var.set("Vivian")
        self.panel_ref_audio_var.set("")
        self.panel_ref_text_var.set("")
        self.panel_xvec_var.set(False)
        self.panel_instruct_box.delete("1.0", "end")
        self._on_profile_mode_change("custom_voice")
        self._refresh_profile_panel_cards()

    def _save_profile_panel(self):
        item = next((p for p in self.profiles if p["id"] == self.profile_form_target_id), None)
        if item is None:
            item = {"id": f"profile_{len(self.profiles)+1}"}
        profile_name = self.panel_name_var.get().strip() or "Profile"
        name_taken = any(p["name"] == profile_name and p["id"] != item["id"] for p in self.profiles)
        if name_taken:
            messagebox.showwarning(t("common.warning", "Warning"), t("qwen3_tts.profile_name_duplicate", "Profile names must be unique."))
            return
        item.update({
            "name": profile_name,
            "mode": self.panel_mode_var.get(),
            "speaker": self.panel_speaker_var.get(),
            "instruct": self.panel_instruct_box.get("1.0", "end").strip(),
            "ref_audio": self.panel_ref_audio_var.get().strip(),
            "ref_text": self.panel_ref_text_var.get().strip(),
            "x_vector_only": bool(self.panel_xvec_var.get()),
        })
        if not any(p["id"] == item["id"] for p in self.profiles):
            self.profiles.append(item)
        self._save_profiles()
        self.profile_var.set(item["name"])
        self.profile_form_target_id = item["id"]
        self._refresh_profiles()
        self._refresh_status_bar()
        self._load_profile_into_panel(item)

    def _browse_ref_audio(self, variable):
        selected = filedialog.askopenfilename(
            title=t("qwen3_tts.ref_audio", "Reference Audio"),
            filetypes=[("Audio Files", "*.wav;*.mp3;*.m4a;*.flac;*.ogg;*.aac"), ("All Files", "*.*")],
        )
        if selected:
            variable.set(selected)

    def _delete_profile_from_panel(self):
        if len(self.profiles) <= 1 or not self.profile_form_target_id:
            return
        current_profile = next((p for p in self.profiles if p["id"] == self.profile_form_target_id), None)
        self.profiles = [p for p in self.profiles if p["id"] != self.profile_form_target_id]
        if current_profile and self.profile_var.get() == current_profile["name"]:
            self.profile_var.set(self.profiles[0]["name"])
        self._save_profiles()
        self._refresh_profiles()
        self._refresh_status_bar()
        self._load_profile_into_panel(self.profiles[0])

    def _cancel_or_close(self):
        if self.current_process:
            kill_process_tree(self.current_process)
            self.current_process = None
            self.generate_btn.configure(state="normal")
            self.status_var.set(t("common.cancelled", "Cancelled"))
            self._hide_overlay()
        else:
            if self.current_playback_path:
                self._stop_playback(redraw=False)
            self.destroy()


def open_qwen3_tts(target_path=None):
    app = Qwen3TTSGUI(target_path)
    app.mainloop()


if __name__ == "__main__":
    open_qwen3_tts()
