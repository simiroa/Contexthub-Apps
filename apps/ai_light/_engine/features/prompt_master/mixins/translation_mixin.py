import customtkinter as ctk
from utils.gui_lib import THEME_BG, THEME_CARD, THEME_BORDER

class TranslationMixin:
    def translate_text(self, text):
        """Translate Korean to English"""
        if not text or not any('\uac00' <= c <= '\ud7a3' for c in text):
            return text
        
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source='ko', target='en')
            result = translator.translate(text)
            return result if result else text
        except Exception as e:
            print(f"Translation error: {e}")
            return text

    def create_input_with_translate(self, parent, input_data, row):
        """Create ONE-LINE input field: Label | Entry | Translate Button"""
        input_id = input_data["id"]
        label_text = input_data.get("label", input_id)
        
        # Label (Right aligned)
        label = ctk.CTkLabel(parent, text=f"{label_text}:", anchor="e")
        label.grid(row=row, column=0, sticky="e", padx=(10, 10), pady=5)
        
        # Entry field (Expandable)
        entry = ctk.CTkEntry(parent, fg_color=THEME_BG, border_color=THEME_BORDER)
        entry.insert(0, input_data.get("default", ""))
        entry.grid(row=row, column=1, sticky="ew", pady=5)
        entry.bind("<KeyRelease>", self.update_output)
        
        # Translate button (Compact)
        translate_btn = ctk.CTkButton(
            parent, 
            text="🌐",
            width=35,
            height=28,
            command=lambda e=entry: self.translate_and_update(e),
            fg_color="#1a1a1a",
            hover_color="#222",
            border_width=1,
            border_color=THEME_BORDER,
            border_spacing=0
        )
        translate_btn.grid(row=row, column=2, padx=(5, 10), pady=5)
        
        self.input_widgets[input_id] = entry

    def translate_and_update(self, entry_widget):
        """Translate on button click"""
        text = entry_widget.get()
        if text:
            translated = self.translate_text(text)
            entry_widget.delete(0, "end")
            entry_widget.insert(0, translated)
            self.update_output()
