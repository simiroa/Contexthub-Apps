import customtkinter as ctk
import tkinter.messagebox
from tkinter import colorchooser
from core.settings import save_settings
from manager.ui.theme import Theme


class CategoriesFrame(ctk.CTkFrame):
    def __init__(self, parent, settings_manager, config_manager):
        super().__init__(parent, fg_color="transparent")
        self.settings = settings_manager # dict
        self.config = config_manager     # Manager instance
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Header
        ctk.CTkLabel(self, text="Category Management", font=ctk.CTkFont(size=20, weight="bold"), text_color=Theme.TEXT_MAIN[1]).grid(row=0, column=0, pady=20)
        
        # Toolbar
        self._setup_toolbar()
        
        # List
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=Theme.BG_MAIN)
        self.scroll_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        
        self.refresh_list()

    def _setup_toolbar(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=20)
        
        ctk.CTkButton(toolbar, text="+ Add Category", command=self.add_category, fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER).pack(side="right", padx=10, pady=10)
        ctk.CTkButton(toolbar, text="Save Changes", command=self.save_changes, fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER).pack(side="right", padx=10, pady=10)

    def refresh_list(self):
        for w in self.scroll_frame.winfo_children(): w.destroy()
        
        # Use Order List if available
        cats_colors = self.settings.get("CATEGORY_COLORS", {})
        order_list = self.settings.get("CATEGORY_ORDER", [])
        
        # Ensure all colors are in order list (robustness)
        for c in cats_colors:
            if c not in order_list:
                order_list.append(c)
        
        # Update setting in case we modified it
        self.settings["CATEGORY_ORDER"] = order_list
        
        for idx, name in enumerate(order_list):
            if name in cats_colors: # Only show if valid
                self._create_row(name, cats_colors[name], idx, len(order_list))

    def _create_row(self, name, color, index, total):
        row = ctk.CTkFrame(self.scroll_frame, fg_color=Theme.BG_CARD)
        row.pack(fill="x", pady=2)
        
        # Order Buttons
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.pack(side="left", padx=5)
        
        if index > 0:
            ctk.CTkButton(btn_frame, text="▲", width=24, height=24, fg_color=Theme.GRAY_BTN, hover_color=Theme.GRAY_BTN_HOVER,
                        command=lambda: self.move_category(name, -1)).pack(side="left", padx=1)
        if index < total - 1:
            ctk.CTkButton(btn_frame, text="▼", width=24, height=24, fg_color=Theme.GRAY_BTN, hover_color=Theme.GRAY_BTN_HOVER,
                        command=lambda: self.move_category(name, 1)).pack(side="left", padx=1)
        
        # Color Box
        color_btn = ctk.CTkButton(row, text="", width=30, height=30, fg_color=color, hover_color=color,
                                command=lambda: self.pick_color(name, color_btn))
        color_btn.pack(side="left", padx=5, pady=5)
        
        # Name
        # User requested to remove numeric prefixes
        # priority_label = f"[{ (index + 1) * 1000 }s]"
        # ctk.CTkLabel(row, text=priority_label, text_color="gray", width=60).pack(side="left", padx=0)
        ctk.CTkLabel(row, text=name, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=5)
        
        # Delete
        ctk.CTkButton(row, text="Delete", width=60, fg_color=Theme.DANGER, hover_color=Theme.DANGER_HOVER,
                    command=lambda: self.delete_category(name)).pack(side="right", padx=5)

    def move_category(self, name, direction):
        order_list = self.settings.get("CATEGORY_ORDER", [])
        if name not in order_list: return
        
        idx = order_list.index(name)
        new_idx = idx + direction
        
        if 0 <= new_idx < len(order_list):
            # Swap
            order_list[idx], order_list[new_idx] = order_list[new_idx], order_list[idx]
            self.refresh_list()
            # Auto-save meant interaction? Or wait for 'Save Changes'?
            # Better to wait for Save Changes for big list ops, but user expects feedback.
            # Let's simple refresh for now.

    def pick_color(self, name, btn):
        color = colorchooser.askcolor(title=f"Color for {name}")
        if color[1]:
            self.settings.setdefault("CATEGORY_COLORS", {})[name] = color[1]
            btn.configure(fg_color=color[1], hover_color=color[1])

    def add_category(self):
        dialog = ctk.CTkInputDialog(text="Enter Category Name:", title="New Category")
        val = dialog.get_input()
        if val:
            if val in self.settings.get("CATEGORY_COLORS", {}):
                tkinter.messagebox.showerror("Error", "Category already exists!")
                return
            
            # Default color
            self.settings.setdefault("CATEGORY_COLORS", {})[val] = "#808080"
            self.settings.setdefault("CATEGORY_ORDER", []).append(val)
            self.refresh_list()

    def delete_category(self, name):
        if tkinter.messagebox.askyesno("Delete", f"Delete category '{name}'?"):
            if name in self.settings.get("CATEGORY_COLORS", {}):
                del self.settings["CATEGORY_COLORS"][name]
            if name in self.settings.get("CATEGORY_ORDER", []):
                self.settings["CATEGORY_ORDER"].remove(name)
            self.refresh_list()

    def save_changes(self):
        try:
            save_settings(self.settings)
            tkinter.messagebox.showinfo("Success", "Categories saved.")
        except Exception as e:
            tkinter.messagebox.showerror("Error", f"Failed to save: {e}")
