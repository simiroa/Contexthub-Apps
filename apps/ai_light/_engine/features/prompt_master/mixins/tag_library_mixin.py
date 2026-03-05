import os
import json
import customtkinter as ctk
from ..constants import TAGS_FILE, TAG_CATEGORIES_FILE
from ..tooltip import Tooltip
from utils.gui_lib import THEME_BG, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER

class TagLibraryMixin:
    def load_tags(self):
        # Load custom tags
        custom_tags = []
        if os.path.exists(TAGS_FILE):
            try:
                with open(TAGS_FILE, 'r', encoding='utf-8') as f:
                    custom_tags = json.load(f).get("custom_tags", [])
            except:
                pass
        return custom_tags

    def load_tag_categories(self):
        # Load preset categories
        categories = []
        if os.path.exists(TAG_CATEGORIES_FILE):
            try:
                with open(TAG_CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                    categories = json.load(f).get("categories", [])
            except:
                pass
        return categories

    def save_tags(self):
        try:
            os.makedirs(os.path.dirname(TAGS_FILE), exist_ok=True)
            with open(TAGS_FILE, 'w', encoding='utf-8') as f:
                json.dump({"custom_tags": self.tags}, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving tags: {e}")

    def build_tag_library_ui(self):
        """Build the Tag Library section with Tabs"""
        # Load categories if not loaded
        if not hasattr(self, 'tag_categories'):
            self.tag_categories = self.load_tag_categories()
        
        # Clear existing
        for widget in self.tag_library_scroll.winfo_children():
            widget.destroy()
            
        # Tool Bar Frame (Search + Actions)
        tool_frame = ctk.CTkFrame(self.tag_library_scroll, fg_color="transparent")
        tool_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        # Center Container for Search + Buttons
        center_container = ctk.CTkFrame(tool_frame, fg_color="transparent")
        center_container.pack(side="top", anchor="center")
        
        # Search Entry (shorter)
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", self.search_tags)
        
        search_entry = ctk.CTkEntry(
            center_container, 
            placeholder_text="🔍 Search...",
            textvariable=self.search_var,
            width=200,
            fg_color=THEME_BG,
            border_color=THEME_BORDER
        )
        search_entry.pack(side="left", padx=(0, 5))
        Tooltip(search_entry, "Search Tags")
        
        # Action Buttons (Right aligned in container)
        # Manage
        manage_btn = ctk.CTkButton(
            center_container, 
            text="⚙️", 
            width=30,
            command=self.manage_tags,
            fg_color=THEME_BG,
            hover_color=THEME_DROPDOWN_HOVER,
            border_width=1,
            border_color=THEME_BORDER,
            border_spacing=0
        )
        manage_btn.pack(side="left", padx=2)
        Tooltip(manage_btn, "Manage Tags")

        # Translate
        translate_btn = ctk.CTkButton(
            center_container, 
            text="🌐", 
            width=30,
            command=self.translate_user_context,
            fg_color=THEME_BG,
            hover_color=THEME_DROPDOWN_HOVER,
            border_width=1,
            border_color=THEME_BORDER,
            border_spacing=0
        )
        translate_btn.pack(side="left", padx=2)
        Tooltip(translate_btn, "Translate Context")

        # Reset
        reset_btn = ctk.CTkButton(
            center_container, 
            text="🔄", 
            width=30,
            command=self.reset_user_context,
            fg_color=THEME_BG,
            hover_color=THEME_DROPDOWN_HOVER,
            border_width=1,
            border_color=THEME_BORDER,
            border_spacing=0
        )
        reset_btn.pack(side="left", padx=2)
        Tooltip(reset_btn, "Reset Context")
        
        # Tab View for Categories
        self.tag_tabs = ctk.CTkTabview(
            self.tag_library_scroll, 
            height=250,
            fg_color=THEME_CARD,
            segmented_button_fg_color=THEME_BG,
            segmented_button_selected_color=THEME_BTN_PRIMARY,
            segmented_button_selected_hover_color=THEME_BTN_HOVER,
            segmented_button_unselected_color=THEME_DROPDOWN_FG,
            segmented_button_unselected_hover_color=THEME_DROPDOWN_BTN,
            text_color="#E0E0E0"
        )
        self.tag_tabs.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create Tabs
        # 1. Custom Tab
        if self.tags:
            self.tag_tabs.add("Custom")
            self.build_tab_content("Custom", self.tags)
            
        # 2. Category Tabs
        for cat in self.tag_categories:
            tab_name = cat["name"]
            self.tag_tabs.add(tab_name)
            self.build_tab_content(tab_name, cat["tags"])

    def reset_user_context(self):
        """Clear the Custom Prompt (User Context)"""
        self.custom_input.delete("0.0", "end")
        self.update_output()
        self.update_tag_visuals()

    def translate_user_context(self):
        """Translate the Custom Prompt (User Context)"""
        text = self.custom_input.get("0.0", "end").strip()
        if not text:
            return
            
        # Use TranslationMixin's logic if available, or direct call
        # Assuming TranslationMixin is mixed in and has translate_text
        if hasattr(self, 'translate_text'):
            translated = self.translate_text(text)
            if translated:
                self.custom_input.delete("0.0", "end")
                self.custom_input.insert("0.0", translated)
                self.update_output()
                self.update_tag_visuals()

    def build_tab_content(self, tab_name, tags):
        """Populate tags within a tab"""
        tab_frame = self.tag_tabs.tab(tab_name)
        
        # Scrollable frame inside tab
        scroll = ctk.CTkScrollableFrame(
            tab_frame, 
            fg_color="transparent", 
            scrollbar_fg_color="transparent",
            scrollbar_button_color="#222",
            scrollbar_button_hover_color="#333"
        )
        scroll.pack(fill="both", expand=True)
        
        self.populate_tags_grid(scroll, tags)

    def search_tags(self, *args):
        """Filter tags across all tabs or show search results"""
        query = self.search_var.get().lower()
        
        if not query:
            # Restore all
            if self.tags:
                try:
                    scroll = self.tag_tabs.tab("Custom").winfo_children()[0]
                    self.populate_tags_grid(scroll, self.tags)
                except: pass
            for cat in self.tag_categories:
                try:
                    scroll = self.tag_tabs.tab(cat["name"]).winfo_children()[0]
                    self.populate_tags_grid(scroll, cat["tags"])
                except: pass
            return

        # Filter
        if self.tags:
            filtered = [t for t in self.tags if query in t.get("id", "").lower() or query in t.get("text", "").lower()]
            try:
                scroll = self.tag_tabs.tab("Custom").winfo_children()[0]
                self.populate_tags_grid(scroll, filtered)
            except: pass
            
        for cat in self.tag_categories:
            try:
                scroll = self.tag_tabs.tab(cat["name"]).winfo_children()[0]
                filtered = [t for t in cat["tags"] if query in t.get("id", "").lower() or query in t.get("text", "").lower()]
                self.populate_tags_grid(scroll, filtered)
            except: pass

    def populate_tags_grid(self, parent, tags):
        # Use Flow Layout (Row-based packing) for better spacing
        for w in parent.winfo_children():
            w.destroy()
            
        # Container for rows
        content_frame = ctk.CTkFrame(parent, fg_color="transparent")
        content_frame.pack(fill="x", expand=True)
        
        current_row_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        current_row_frame.pack(fill="x", pady=2)
        
        # We can't easily detect width overflow in CTk without complex event handling.
        # So we'll use a max-items-per-row approach but with pack to keep them compact.
        # Or just pack them all and let them wrap? CTk doesn't auto-wrap.
        # Let's stick to a safe number of items per row, but pack them to the left.
        
        max_per_row = 6
        count = 0
        
        for tag in tags:
            btn = ctk.CTkButton(
                current_row_frame,
                text=tag.get("id", ""),
                command=lambda t=tag: self.add_tag(t),
                height=24,
                width=20, # Auto-width (min 20)
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                border_width=1,
                border_color=THEME_BORDER,
                hover_color=THEME_DROPDOWN_HOVER
            )
            btn.pack(side="left", padx=2)
            
            count += 1
            if count >= max_per_row:
                count = 0
                current_row_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
                current_row_frame.pack(fill="x", pady=2)

        # Initial visual update
        self.update_tag_visuals()

    def add_tag(self, tag):
        """Add tag text to Custom Prompt (User Context)"""
        tag_text = tag.get("text", "")
        if not tag_text:
            return
            
        current_text = self.custom_input.get("0.0", "end").strip()
        
        # Toggle logic
        if tag_text in current_text:
            # Remove
            new_text = current_text.replace(f", {tag_text}", "").replace(f"{tag_text}, ", "").replace(tag_text, "")
            new_text = new_text.replace(", ,", ",").strip(", ")
        else:
            # Add
            if current_text:
                new_text = f"{current_text}, {tag_text}"
            else:
                new_text = tag_text
            
        self.custom_input.delete("0.0", "end")
        self.custom_input.insert("0.0", new_text)
        
        self.update_output()
        self.update_tag_visuals()

    def update_tag_visuals(self, event=None):
        """Update button colors based on Custom Prompt content"""
        current_text = self.custom_input.get("0.0", "end").strip()
        
        # Helper to update a scrollable frame content
        def update_container(container):
            # The container has a content_frame which has row_frames
            # We need to traverse down
            for child in container.winfo_children():
                # This might be content_frame
                if isinstance(child, ctk.CTkFrame):
                    for row_frame in child.winfo_children():
                        if isinstance(row_frame, ctk.CTkFrame):
                            for widget in row_frame.winfo_children():
                                if isinstance(widget, ctk.CTkButton):
                                    tag_id = widget.cget("text")
                                    # Find tag text
                                    found_text = ""
                                    for t in self.tags:
                                        if t["id"] == tag_id:
                                            found_text = t["text"]
                                            break
                                    if not found_text:
                                        for cat in self.tag_categories:
                                            for t in cat["tags"]:
                                                if t["id"] == tag_id:
                                                    found_text = t["text"]
                                                    break
                                            if found_text: break
                                    
                                    if found_text and found_text in current_text:
                                        widget.configure(fg_color="#1E4620", border_color="#2E7D32") # Darker green
                                    else:
                                        widget.configure(fg_color="transparent", border_color=THEME_BORDER)

        # Update Custom Tab
        try:
            custom_scroll = self.tag_tabs.tab("Custom").winfo_children()[0]
            update_container(custom_scroll)
        except: pass
        
        # Update Category Tabs
        for cat in self.tag_categories:
            try:
                cat_scroll = self.tag_tabs.tab(cat["name"]).winfo_children()[0]
                update_container(cat_scroll)
            except: pass


    def manage_tags(self):
        """Tag management window"""
        tag_window = ctk.CTkToplevel(self)
        tag_window.title("Manage Tags")
        tag_window.geometry("500x600")
        
        title = ctk.CTkLabel(tag_window, text="🏷️ Tag Manager", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(pady=20, padx=20)
        
        list_frame = ctk.CTkScrollableFrame(tag_window, height=350)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        def refresh_tag_list():
            for widget in list_frame.winfo_children():
                widget.destroy()
            
            for tag in self.tags:
                tag_frame = ctk.CTkFrame(list_frame, fg_color="gray20")
                tag_frame.pack(fill="x", padx=5, pady=5)
                
                label = ctk.CTkLabel(tag_frame, text=f"{tag.get('id', '')}: {tag.get('text', '')}", anchor="w")
                label.pack(side="left", fill="x", expand=True, padx=10, pady=10)
                
                delete_btn = ctk.CTkButton(
                    tag_frame,
                    text="❌",
                    width=30,
                    fg_color="red",
                    command=lambda t=tag: remove_tag(t)
                )
                delete_btn.pack(side="right", padx=5)
        
        def remove_tag(tag):
            self.tags.remove(tag)
            self.save_tags()
            refresh_tag_list()
            self.build_tag_library_ui() # Rebuild main UI
        
        def add_tag():
            add_window = ctk.CTkToplevel(tag_window)
            add_window.title("Add Tag")
            add_window.geometry("500x400")
            
            ctk.CTkLabel(add_window, text="Tag ID:").pack(pady=(20, 5))
            id_entry = ctk.CTkEntry(add_window, width=300)
            id_entry.pack(pady=(0, 10))
            
            ctk.CTkLabel(add_window, text="Tag Text:").pack(pady=(10, 5))
            text_entry = ctk.CTkEntry(add_window, width=300)
            text_entry.pack(pady=(0, 20))
            
            def save_new_tag():
                tag_id = id_entry.get().strip()
                tag_text = text_entry.get().strip()
                
                if tag_id and tag_text:
                    self.tags.append({"id": tag_id, "text": tag_text})
                    self.save_tags()
                    refresh_tag_list()
                    self.build_tag_library_ui() # Rebuild main UI
                    add_window.destroy()
            
            ctk.CTkButton(add_window, text="Add", command=save_new_tag).pack()
        
        refresh_tag_list()
        add_btn = ctk.CTkButton(tag_window, text="➕ Add New Tag", command=add_tag, height=40)
        add_btn.pack(pady=10, padx=20, fill="x")


