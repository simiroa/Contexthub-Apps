from __future__ import annotations

import os
import threading
from pathlib import Path

from contexthub.ui.flet.dialogs import build_progress_dialog
from contexthub.ui.flet.layout import action_bar, apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import (
    COLORS,
    CONTROL_WIDTHS,
    RADII,
    SIZES,
    SPACING,
    WINDOWS,
    mode_color,
    profile_color_seed,
    status_color,
)
from features.ai.standalone.qwen3_tts_service import (
    SUPPORTED_LANGUAGES,
    TONE_PRESETS,
    build_job,
    clone_quality_status,
    ensure_unique_profile_name,
    load_profiles,
    prefill_messages,
    profile_by_name,
    profile_names,
    run_jobs_sync,
    save_profiles,
)
from features.ai.standalone.qwen3_tts_state import AppState, MessageState


class Qwen3TTSFletApp:
    def __init__(self, page, target_path=None):
        import flet as ft

        self.ft = ft
        self.page = page
        configure_page(self.page, "Qwen3 TTS", window_profile="wide_canvas")

        self.state = AppState()
        self.profiles = load_profiles()
        self.target_path = Path(target_path) if target_path else None
        initial_messages, self.profiles = prefill_messages(self.target_path, self.profiles, "Hello from ContextHub. This is a quick voice test.")
        self.state.messages = [MessageState(**item) for item in initial_messages]
        self.selected_profile_name = self.profiles[0]["name"]
        self.selected_tone = "natural"
        self.selected_language = "Auto"
        self.selected_device = "cuda"
        self.output_dir = Path.home() / "Documents"

        self.composer_text = ft.TextField(value="Hello from ContextHub. This is a quick voice test.", multiline=True, min_lines=3, max_lines=6, border_radius=RADII["md"], bgcolor=COLORS["surface"], border_color=COLORS["line"], color=COLORS["text"])
        self.profile_dropdown = ft.Dropdown(label="Profile", value=self.selected_profile_name, options=[ft.dropdown.Option(name) for name in profile_names(self.profiles)], width=CONTROL_WIDTHS["profile"])
        self.tone_dropdown = ft.Dropdown(label="Tone", value=self.selected_tone, options=[ft.dropdown.Option(name) for name in TONE_PRESETS.keys()], width=CONTROL_WIDTHS["tone"])
        self.language_dropdown = ft.Dropdown(label="Language", value=self.selected_language, options=[ft.dropdown.Option(name) for name in SUPPORTED_LANGUAGES], width=CONTROL_WIDTHS["language"])
        self.status_text = ft.Text(self.state.status_text, color=COLORS["text_muted"])
        self.message_column = ft.Column(spacing=SPACING["sm"], scroll=ft.ScrollMode.AUTO, expand=True)
        self.profile_panel_container = ft.Container(width=WINDOWS["side_panel_width"], visible=False)
        self.overlay_dialog = self._build_overlay_dialog()

        self.panel_name = ft.TextField(label="Profile Name")
        self.panel_mode = ft.Dropdown(label="Mode", value="custom_voice", options=[ft.dropdown.Option("custom_voice"), ft.dropdown.Option("voice_clone"), ft.dropdown.Option("voice_design")])
        self.panel_mode.on_change = self._on_panel_mode_change
        self.panel_speaker = ft.Dropdown(label="Speaker", value="Vivian", options=[ft.dropdown.Option(name) for name in ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]])
        self.panel_instruct = ft.TextField(label="Style Instruction", multiline=True, min_lines=3, max_lines=5)
        self.panel_ref_audio = ft.TextField(label="Reference Audio")
        self.panel_ref_text = ft.TextField(label="Reference Transcript")
        self.panel_mode_hint = ft.Text("", color=COLORS["text_muted"])
        self.profile_form_target_id = None
        self.panel_status = ft.Text("", color=COLORS["text_muted"])

        self.page.add(self._build_layout())
        self._render()

    @staticmethod
    def _mode_label(mode: str) -> str:
        return {
            "custom_voice": "Preset Voice",
            "voice_clone": "Clone from Audio",
            "voice_design": "Design New Voice",
        }.get(mode, mode.replace("_", " ").title())

    @staticmethod
    def _mode_hint(mode: str) -> str:
        return {
            "custom_voice": "Built-in speaker with instruction-driven tone shaping.",
            "voice_clone": "Reference audio and transcript are used to match a target voice.",
            "voice_design": "A new character voice is described in natural language.",
        }.get(mode, "")

    def _build_overlay_dialog(self):
        built = build_progress_dialog(self.ft, "Preparing generation...", "", on_cancel=lambda e: self._close_overlay())
        self.overlay_title = built["title"]
        self.overlay_hint = built["hint"]
        self.overlay_progress = built["progress"]
        return built["dialog"]

    def _build_layout(self):
        ft = self.ft
        return ft.Container(
            expand=True,
            padding=ft.padding.all(SPACING["lg"]),
            content=ft.Column(
                expand=True,
                controls=[
                    self._build_header(),
                    ft.Row(
                        expand=True,
                        spacing=SPACING["md"],
                        controls=[
                            ft.Container(expand=True, content=self.message_column),
                            self.profile_panel_container,
                        ],
                    ),
                    self._build_composer(),
                ],
            ),
        )

    def _build_header(self):
        ft = self.ft
        return ft.Container(
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            padding=SPACING["lg"],
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Text("Qwen3-TTS · 1.7B", size=22, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ft.Text(
                        f"Model 1.7B ready · Device: {self.selected_device} · Profiles: {len(self.profiles)}",
                        color=COLORS["text"],
                    ),
                    ft.Text(
                        "Click a bubble to edit, regenerate, delete, or swap voice profile.",
                        color=COLORS["text_muted"],
                    ),
                ],
            ),
        )

    def _build_composer(self):
        ft = self.ft
        return ft.Container(
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            padding=SPACING["md"],
            content=ft.Column(
                controls=[
                    ft.Row(
                        wrap=True,
                        controls=[
                            self.profile_dropdown,
                            self.tone_dropdown,
                            self.language_dropdown,
                            apply_button_sizing(ft.OutlinedButton("Profiles", on_click=lambda e: self._toggle_profile_panel()), "toolbar"),
                        ],
                    ),
                    self.composer_text,
                    action_bar(
                        status=self.status_text,
                        primary=apply_button_sizing(
                            ft.ElevatedButton("Generate Conversation", on_click=lambda e: self._generate_all(), bgcolor=COLORS["accent"], color="#FFFFFF"),
                            "primary",
                        ),
                        secondary=[
                            apply_button_sizing(ft.OutlinedButton("Add Bubble", on_click=lambda e: self._add_message()), "compact"),
                            apply_button_sizing(ft.OutlinedButton("Open Folder", on_click=lambda e: self._open_output_folder()), "compact"),
                        ],
                    ),
                ]
            ),
        )

    def _toggle_profile_panel(self):
        self.state.profile_panel_open = not self.state.profile_panel_open
        self._render()

    def _close_overlay(self):
        self.overlay_dialog.open = False
        self.page.update()

    def _render(self):
        ft = self.ft
        self.message_column.controls = [self._message_card(message) for message in self.state.messages]
        self.profile_dropdown.options = [ft.dropdown.Option(name) for name in profile_names(self.profiles)]
        self.profile_dropdown.value = self.selected_profile_name
        self.tone_dropdown.value = self.selected_tone
        self.language_dropdown.value = self.selected_language
        self.status_text.value = self.state.status_text
        self.profile_panel_container.visible = self.state.profile_panel_open
        if self.state.profile_panel_open:
            self.profile_panel_container.content = self._build_profile_panel()
        self.page.update()

    def _message_card(self, message):
        ft = self.ft
        profile = profile_by_name(self.profiles, message.profile)
        quality = clone_quality_status(profile)
        profile_drop = ft.Dropdown(label="Profile", value=message.profile, width=CONTROL_WIDTHS["profile"], options=[ft.dropdown.Option(name) for name in profile_names(self.profiles)])
        profile_drop.on_change = lambda e, mid=message.id: self._update_message_profile(mid, e.control.value)
        tone_drop = ft.Dropdown(label="Tone", value=message.tone, width=CONTROL_WIDTHS["tone"], options=[ft.dropdown.Option(name) for name in TONE_PRESETS.keys()])
        tone_drop.on_change = lambda e, mid=message.id: self._update_message_tone(mid, e.control.value)
        detail_controls = [
            ft.Row(
                wrap=True,
                controls=[
                    profile_drop,
                    tone_drop,
                    apply_button_sizing(ft.OutlinedButton("Edit Profile", on_click=lambda e, name=message.profile: self._open_profile_for(name)), "compact"),
                ]
            ),
            apply_button_sizing(ft.OutlinedButton("Edit Text", on_click=lambda e, mid=message.id: self._toggle_text_edit(mid)), "compact"),
        ]
        if self.state.editing_text_message_id == message.id:
            editor_box = ft.TextField(value=message.text, multiline=True, min_lines=4, max_lines=8, border_radius=RADII["md"], bgcolor=COLORS["field_bg"], border_color=COLORS["line"])
            detail_controls.append(
                ft.Container(
                    bgcolor=COLORS["surface_alt"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["md"],
                    padding=SPACING["sm"],
                    content=ft.Column(
                        controls=[
                            editor_box,
                            ft.Row(
                                wrap=True,
                                controls=[
                                    ft.ElevatedButton("Apply Text", on_click=lambda e, mid=message.id, box=editor_box: self._apply_message_text(mid, box.value)),
                                    ft.TextButton("Cancel", on_click=lambda e, mid=message.id: self._toggle_text_edit(mid)),
                                ]
                            ),
                        ]
                    ),
                )
            )
        action_row = ft.Row(
            wrap=True,
            controls=[
                apply_button_sizing(ft.ElevatedButton("Generate This", on_click=lambda e, mid=message.id: self._generate_one(mid), bgcolor=COLORS["accent"], color="#FFFFFF"), "compact"),
                apply_button_sizing(ft.OutlinedButton("More", on_click=lambda e, mid=message.id: self._toggle_more(mid)), "compact"),
            ]
        )
        if self.state.expanded_actions_message_id == message.id:
            detail_controls.append(
                ft.Container(
                    bgcolor=COLORS["surface_soft"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["md"],
                    padding=SPACING["sm"],
                    content=ft.Row(
                        wrap=True,
                        controls=[
                            apply_button_sizing(ft.OutlinedButton("Use Composer Settings", on_click=lambda e, mid=message.id: self._apply_composer(mid)), "compact"),
                            apply_button_sizing(ft.TextButton("Delete", on_click=lambda e, mid=message.id: self._delete_message(mid)), "compact"),
                        ]
                    ),
                )
            )
        if quality:
            detail_controls.insert(0, ft.Text(f"Clone Status: {quality[1]}", color=COLORS["text_muted"]))
        detail_controls.insert(
            0,
            ft.Text(
                self._mode_hint(profile.get("mode", "custom_voice")),
                color=COLORS["text_muted"],
            ),
        )
        result_card = None
        if message.output:
            result_info = [ft.Text(f"Type: {self._mode_label(profile.get('mode', 'custom_voice'))}", color=COLORS["text_muted"])]
            if profile.get("mode") == "voice_clone":
                result_info.append(ft.Text(f"Reference: {Path(profile.get('ref_audio', '')).name}", color=COLORS["text_muted"]))
            result_card = ft.Container(
                bgcolor=COLORS["surface_accent"],
                border=ft.border.all(1, COLORS["line"]),
                border_radius=RADII["md"],
                padding=SPACING["sm"],
                content=ft.Column(
                    controls=[
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Generated Result", weight=ft.FontWeight.BOLD, color=COLORS["text"]), ft.Text(message.output, size=10, color=COLORS["text_soft"])]),
                        ft.Row(controls=result_info),
                        ft.Row(
                            wrap=True,
                            controls=[
                                apply_button_sizing(ft.OutlinedButton("Play Result", on_click=lambda e, output=message.output: self._open_output_file(output)), "compact"),
                                apply_button_sizing(ft.OutlinedButton("Reveal File", on_click=lambda e, output=message.output: self._reveal_output_file(output)), "compact"),
                                apply_button_sizing(ft.OutlinedButton("Regenerate", on_click=lambda e, mid=message.id: self._generate_one(mid)), "compact"),
                            ]
                        ),
                    ]
                ),
            )

        content = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(message.role, weight=ft.FontWeight.BOLD, size=18, color=COLORS["text"]),
                    ft.Row(
                        controls=[
                            ft.Container(
                                bgcolor=mode_color(profile.get("mode", "custom_voice")),
                                border_radius=RADII["pill"],
                                padding=ft.padding.symmetric(horizontal=SIZES["badge_horizontal"], vertical=SIZES["badge_vertical"]),
                                content=ft.Text(self._mode_label(profile.get("mode", "custom_voice")), size=11, color="#FFFFFF"),
                            ),
                            ft.Text(message.profile, color=COLORS["text_muted"]),
                            ft.Text(message.tone, color=COLORS["text_muted"]),
                            ft.Container(bgcolor=status_color(message.status), border_radius=RADII["pill"], padding=ft.padding.symmetric(horizontal=SIZES["badge_horizontal"], vertical=SIZES["badge_vertical"]), content=ft.Text(message.status, size=11, color="#FFFFFF")),
                        ]
                    ),
                ],
            ),
            ft.Text(message.text, color=COLORS["text"]),
        ]
        if self.state.selected_message_id == message.id:
            content.append(ft.Container(bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line_strong"]), border_radius=RADII["md"], padding=SPACING["sm"], content=ft.Column(controls=detail_controls + [action_row] + ([result_card] if result_card else []))))

        return ft.Container(
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line_strong"] if self.state.selected_message_id == message.id else COLORS["line"]),
            border_radius=RADII["xl"],
            padding=SIZES["message_padding"],
            on_click=lambda e, mid=message.id: self._select_message(mid),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Container(width=SIZES["avatar"], height=SIZES["avatar"], border_radius=SIZES["avatar_radius"], bgcolor=profile_color_seed(message.profile), alignment=ft.alignment.Alignment(0, 0), content=ft.Text((message.role[:1] or "?").upper(), color="#FFFFFF", weight=ft.FontWeight.BOLD)),
                    ft.Container(expand=True, content=ft.Column(controls=content)),
                ],
            ),
        )

    def _build_profile_panel(self):
        ft = self.ft
        cards = []
        for profile in self.profiles:
            quality = clone_quality_status(profile)
            extra = []
            if quality:
                extra.append(ft.Container(bgcolor=COLORS["info"], border_radius=RADII["pill"], padding=ft.padding.symmetric(horizontal=SIZES["mini_badge_horizontal"], vertical=SIZES["mini_badge_vertical"]), content=ft.Text(quality[1], size=11)))
            cards.append(
                ft.Container(
                    bgcolor=COLORS["surface"],
                    border=ft.border.all(1, COLORS["line_strong"] if profile["id"] == self.profile_form_target_id else COLORS["line"]),
                    border_radius=RADII["md"],
                    padding=SPACING["sm"],
                    on_click=lambda e, p=profile: self._load_profile_into_panel(p),
                    content=ft.Column(
                        controls=[
                            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(profile["name"], weight=ft.FontWeight.BOLD, color=COLORS["text"]), ft.Text(self._mode_label(profile["mode"]), color=COLORS["text_muted"])]),
                            ft.Text((profile.get("instruct") or profile.get("ref_audio") or "")[:90], size=12, color=COLORS["text_muted"]),
                            ft.Row(controls=extra),
                        ]
                    ),
                )
            )
        return ft.Container(
            bgcolor=COLORS["surface_alt"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            padding=SPACING["md"],
            content=ft.Column(
                controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Voice Profiles", size=18, weight=ft.FontWeight.BOLD), ft.TextButton("Close", on_click=lambda e: self._toggle_profile_panel())]),
                    ft.Column(controls=cards, scroll=ft.ScrollMode.AUTO, height=SIZES["profile_list_height"]),
                    self.panel_name,
                    self.panel_mode,
                    self.panel_mode_hint,
                    self.panel_speaker if self.panel_mode.value == "custom_voice" else ft.Container(),
                    self.panel_instruct if self.panel_mode.value in {"custom_voice", "voice_design"} else ft.Container(),
                    self.panel_ref_audio if self.panel_mode.value == "voice_clone" else ft.Container(),
                    self.panel_ref_text if self.panel_mode.value == "voice_clone" else ft.Container(),
                    ft.Row(
                        wrap=True,
                        controls=[
                            apply_button_sizing(ft.ElevatedButton("Save", on_click=lambda e: self._save_profile()), "compact"),
                            apply_button_sizing(ft.OutlinedButton("Add Profile", on_click=lambda e: self._new_profile()), "compact"),
                            apply_button_sizing(ft.TextButton("Delete", on_click=lambda e: self._delete_profile()), "compact"),
                        ]
                    ),
                    self.panel_status,
                ]
            ),
        )

    def _on_panel_mode_change(self, e):
        mode = e.control.value if hasattr(e, "control") else e
        hints = {
            "custom_voice": "Fastest path. Pick a built-in speaker and shape the delivery with instruction.",
            "voice_clone": "Best for matching a real voice. Add a clean reference clip and matching transcript.",
            "voice_design": "Describe a new voice character in natural language and let Qwen design it.",
        }
        self.panel_mode_hint.value = hints.get(mode, "")
        self._render()

    def _load_profile_into_panel(self, profile):
        self.profile_form_target_id = profile["id"]
        self.panel_name.value = profile["name"]
        self.panel_mode.value = profile["mode"]
        self.panel_speaker.value = profile["speaker"]
        self.panel_instruct.value = profile.get("instruct", "")
        self.panel_ref_audio.value = profile.get("ref_audio", "")
        self.panel_ref_text.value = profile.get("ref_text", "")
        self._on_panel_mode_change(profile["mode"])

    def _new_profile(self):
        self.profile_form_target_id = None
        self.panel_name.value = ""
        self.panel_mode.value = "custom_voice"
        self.panel_speaker.value = "Vivian"
        self.panel_instruct.value = ""
        self.panel_ref_audio.value = ""
        self.panel_ref_text.value = ""
        self.panel_status.value = ""
        self._on_panel_mode_change("custom_voice")

    def _save_profile(self):
        item = next((profile for profile in self.profiles if profile["id"] == self.profile_form_target_id), None)
        if item is None:
            item = {"id": f"profile_{len(self.profiles)+1}"}
        name = (self.panel_name.value or "").strip() or "Profile"
        if not ensure_unique_profile_name(self.profiles, name, item["id"]):
            self.panel_status.value = "Profile names must be unique."
            self._render()
            return
        item.update(
            {
                "name": name,
                "mode": self.panel_mode.value,
                "speaker": self.panel_speaker.value,
                "instruct": self.panel_instruct.value or "",
                "ref_audio": self.panel_ref_audio.value or "",
                "ref_text": self.panel_ref_text.value or "",
                "x_vector_only": False,
            }
        )
        if not any(profile["id"] == item["id"] for profile in self.profiles):
            self.profiles.append(item)
        save_profiles(self.profiles)
        self.selected_profile_name = item["name"]
        self.panel_status.value = "Profile saved."
        self._load_profile_into_panel(item)
        self._render()

    def _delete_profile(self):
        if len(self.profiles) <= 1 or not self.profile_form_target_id:
            return
        self.profiles = [profile for profile in self.profiles if profile["id"] != self.profile_form_target_id]
        save_profiles(self.profiles)
        self._load_profile_into_panel(self.profiles[0])
        self._render()

    def _open_profile_for(self, profile_name):
        self.state.profile_panel_open = True
        self._load_profile_into_panel(profile_by_name(self.profiles, profile_name))
        self._render()

    def _select_message(self, message_id):
        self.state.selected_message_id = message_id
        message = next(message for message in self.state.messages if message.id == message_id)
        self.composer_text.value = message.text
        self.selected_profile_name = message.profile
        self.selected_tone = message.tone
        self._render()

    def _toggle_more(self, message_id):
        self.state.expanded_actions_message_id = None if self.state.expanded_actions_message_id == message_id else message_id
        self._render()

    def _toggle_text_edit(self, message_id):
        self.state.editing_text_message_id = None if self.state.editing_text_message_id == message_id else message_id
        self._render()

    def _apply_message_text(self, message_id, text):
        message = next(message for message in self.state.messages if message.id == message_id)
        message.text = text
        self.state.editing_text_message_id = None
        self.composer_text.value = text
        self._render()

    def _update_message_profile(self, message_id, profile_name):
        message = next(message for message in self.state.messages if message.id == message_id)
        message.profile = profile_name
        self.selected_profile_name = profile_name
        self._render()

    def _update_message_tone(self, message_id, tone_name):
        message = next(message for message in self.state.messages if message.id == message_id)
        message.tone = tone_name
        self.selected_tone = tone_name
        self._render()

    def _apply_composer(self, message_id):
        message = next(message for message in self.state.messages if message.id == message_id)
        message.profile = self.profile_dropdown.value
        message.tone = self.tone_dropdown.value
        self._render()

    def _delete_message(self, message_id):
        self.state.messages = [message for message in self.state.messages if message.id != message_id]
        self.state.selected_message_id = None
        self._render()

    def _open_output_folder(self):
        try:
            os.startfile(self.output_dir)
        except Exception as exc:
            self.state.status_text = f"Could not open folder: {exc}"
            self._render()

    def _open_output_file(self, output_path):
        try:
            os.startfile(output_path)
        except Exception as exc:
            self.state.status_text = f"Could not open file: {exc}"
            self._render()

    def _reveal_output_file(self, output_path):
        try:
            os.startfile(Path(output_path).parent)
        except Exception as exc:
            self.state.status_text = f"Could not reveal file: {exc}"
            self._render()

    def _add_message(self):
        text = (self.composer_text.value or "").strip()
        if not text:
            self.state.status_text = "Text is required."
            self._render()
            return
        if self.state.selected_message_id:
            message = next(message for message in self.state.messages if message.id == self.state.selected_message_id)
            message.profile = self.profile_dropdown.value
            message.tone = self.tone_dropdown.value
            message.text = text
        else:
            self.state.messages.append(
                MessageState(
                    id=f"msg_{len(self.state.messages)+1}",
                    role=self.profile_dropdown.value,
                    profile=self.profile_dropdown.value,
                    tone=self.tone_dropdown.value,
                    text=text,
                )
            )
        self.state.selected_message_id = None
        self._render()

    def _open_overlay(self, title, hint, progress):
        self.overlay_title.value = title
        self.overlay_hint.value = hint
        self.overlay_progress.value = progress
        self.page.dialog = self.overlay_dialog
        self.overlay_dialog.open = True
        self.page.update()

    def _set_overlay_progress(self, current, total):
        total = max(total, 1)
        self.overlay_hint.value = f"{current} / {total}"
        self.overlay_progress.value = current / total
        self.page.update()

    def _close_generation_dialog(self):
        self.overlay_dialog.open = False
        self.page.update()

    def _generate_one(self, message_id):
        selected = next(message for message in self.state.messages if message.id == message_id)
        self._generate_messages([selected])

    def _generate_all(self):
        self._generate_messages(self.state.messages)

    def _generate_messages(self, messages):
        jobs = []
        active_messages = []
        try:
            for idx, message in enumerate(messages, start=1):
                if not message.text.strip():
                    continue
                job = build_job(message.__dict__, self.profiles, self.selected_device, self.language_dropdown.value or "Auto")
                job["file_name"] = f"{idx:03d}_{message.role.lower().replace(' ', '_')}.wav"
                jobs.append(job)
                active_messages.append(message)
        except Exception as exc:
            self.state.status_text = str(exc)
            self._render()
            return

        if not jobs:
            self.state.status_text = "Add at least one dialogue line."
            self._render()
            return

        for message in active_messages:
            message.status = "queued"
        self._open_overlay("Preparing generation...", f"0 / {len(active_messages)}", 0)
        self._render()

        def worker():
            def on_line(line):
                if "[INFO] Generating job " in line:
                    try:
                        progress = line.split("Generating job ", 1)[1].split(":", 1)[0]
                        current, total = progress.split("/")
                        self._set_overlay_progress(int(current), int(total))
                    except Exception:
                        pass

            ok, payload, stdout = run_jobs_sync(jobs, self.output_dir, self.selected_device, on_line=on_line)
            if ok and payload:
                outputs = payload.get("outputs", [])
                for idx, message in enumerate(active_messages):
                    message.status = "done"
                    if idx < len(outputs):
                        message.output = outputs[idx]["output"]
                self.state.status_text = "Speech generated successfully."
            else:
                for message in active_messages:
                    message.status = "error"
                self.state.status_text = stdout or "Generation failed."
            self._close_generation_dialog()
            self._render()

        threading.Thread(target=worker, daemon=True).start()


def open_qwen3_tts_flet(target_path=None):
    import flet as ft

    def main(page: ft.Page):
        Qwen3TTSFletApp(page, target_path=target_path)

    ft.app(target=main)
