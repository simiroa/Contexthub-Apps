import customtkinter as ctk
import tkinter.filedialog
import time
from tkinter import messagebox
from PIL import Image
from pathlib import Path

class ItemEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, item_data=None, on_save=None, on_delete=None):
        super().__init__(parent)
        self.title("Edit Menu Item" if item_data else "Add New Item")
        self.geometry("600x750")
        self.item_data = item_data
        self.on_save_callback = on_save
        self.on_delete_callback = on_delete
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.frame = ctk.CTkFrame(self)
        self.frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.frame.grid_columnconfigure(1, weight=1)
        
        # Name
        ctk.CTkLabel(self.frame, text="Name:").grid(row=0, column=0, sticky="w", pady=10, padx=10)
        self.entry_name = ctk.CTkEntry(self.frame)
        self.entry_name.grid(row=0, column=1, sticky="ew", pady=10, padx=10)
        
        # Category
        ctk.CTkLabel(self.frame, text="Category:").grid(row=1, column=0, sticky="w", pady=10, padx=10)
        # Assuming parent has settings or we pass categories
        categories = list(parent.settings.get("CATEGORY_COLORS", {}).keys())
        if "Custom" not in categories: categories.append("Custom")
        self.combo_category = ctk.CTkComboBox(self.frame, values=categories)
        self.combo_category.grid(row=1, column=1, sticky="ew", pady=10, padx=10)
        self.combo_category.set("Custom")
        
        # Command
        ctk.CTkLabel(self.frame, text="Command:").grid(row=2, column=0, sticky="w", pady=10, padx=10)
        self.entry_command = ctk.CTkEntry(self.frame, placeholder_text="e.g. notepad.exe \"%1\"")
        self.entry_command.grid(row=2, column=1, sticky="ew", pady=10, padx=10)
        
        # Icon
        ctk.CTkLabel(self.frame, text="Icon Path:").grid(row=3, column=0, sticky="w", pady=10, padx=10)
        self.entry_icon = ctk.CTkEntry(self.frame)
        self.entry_icon.grid(row=3, column=1, sticky="ew", pady=10, padx=10)
        ctk.CTkButton(self.frame, text="Browse", width=60, command=self.browse_icon).grid(row=3, column=2, padx=5)
        
        # Types
        ctk.CTkLabel(self.frame, text="File Types:").grid(row=4, column=0, sticky="w", pady=10, padx=10)
        self.entry_types = ctk.CTkEntry(self.frame, placeholder_text="e.g. .jpg;.png or *")
        self.entry_types.grid(row=4, column=1, sticky="ew", pady=10, padx=10)
        
        # Scope
        ctk.CTkLabel(self.frame, text="Scope:").grid(row=5, column=0, sticky="w", pady=10, padx=10)
        self.combo_scope = ctk.CTkComboBox(self.frame, values=["file", "folder", "both"])
        self.combo_scope.grid(row=5, column=1, sticky="ew", pady=10, padx=10)
        self.combo_scope.set("file")

        # Submenu
        ctk.CTkLabel(self.frame, text="Submenu:").grid(row=6, column=0, sticky="w", pady=10, padx=10)
        self.combo_submenu = ctk.CTkComboBox(self.frame, values=["ContextUp", "(Top Level)", "Custom..."])
        self.combo_submenu.grid(row=6, column=1, sticky="ew", pady=10, padx=10)
        self.combo_submenu.set("ContextUp")
        
        # Order (Auto-Calculated)
        ctk.CTkLabel(self.frame, text="Order (Auto):").grid(row=7, column=0, sticky="w", pady=10, padx=10)
        self.entry_order = ctk.CTkEntry(self.frame, placeholder_text="Auto-assigned")
        self.entry_order.configure(state="disabled")
        self.entry_order.grid(row=7, column=1, sticky="ew", pady=10, padx=10)
        
        # Hotkey
        ctk.CTkLabel(self.frame, text="Hotkey:").grid(row=8, column=0, sticky="w", pady=10, padx=10)
        self.hk_var = ctk.StringVar()
        self.entry_hotkey = ctk.CTkEntry(self.frame, textvariable=self.hk_var, state="readonly", placeholder_text="Click Record to set")
        self.entry_hotkey.grid(row=8, column=1, sticky="ew", pady=10, padx=10)
        self.btn_record = ctk.CTkButton(self.frame, text="Record", width=60, command=self.toggle_hotkey_recording)
        self.btn_record.grid(row=8, column=2, padx=5)
        self.is_recording = False
        self.recorded_keys = set()
        
        # Enabled
        ctk.CTkLabel(self.frame, text="Enabled:").grid(row=9, column=0, sticky="w", pady=10, padx=10)
        self.enabled_var = ctk.BooleanVar(value=True)
        self.chk_enabled = ctk.CTkCheckBox(self.frame, text="Active", variable=self.enabled_var)
        self.chk_enabled.grid(row=9, column=1, sticky="w", pady=10, padx=10)
        
        # GUI (Opens Window)
        ctk.CTkLabel(self.frame, text="GUI:").grid(row=10, column=0, sticky="w", pady=10, padx=10)
        self.gui_var = ctk.BooleanVar(value=True)
        self.chk_gui = ctk.CTkCheckBox(self.frame, text="Opens GUI Window", variable=self.gui_var)
        self.chk_gui.grid(row=10, column=1, sticky="w", pady=10, padx=10)

        # Show in Tray
        ctk.CTkLabel(self.frame, text="Tray:").grid(row=11, column=0, sticky="w", pady=10, padx=10)
        self.tray_var = ctk.BooleanVar(value=False)
        self.chk_tray = ctk.CTkCheckBox(self.frame, text="Show in Tray Menu", variable=self.tray_var)
        self.chk_tray.grid(row=11, column=1, sticky="w", pady=10, padx=10)

        # Environment
        ctk.CTkLabel(self.frame, text="Env:").grid(row=12, column=0, sticky="w", pady=10, padx=10)
        self.combo_env = ctk.CTkComboBox(self.frame, values=["system", "internal", "conda"])
        self.combo_env.grid(row=12, column=1, sticky="ew", pady=10, padx=10)
        self.combo_env.set("system")

        # Description
        ctk.CTkLabel(self.frame, text="Desc:").grid(row=13, column=0, sticky="nw", pady=10, padx=10)
        self.entry_desc = ctk.CTkEntry(self.frame, placeholder_text="Feature description...")
        self.entry_desc.grid(row=13, column=1, sticky="ew", pady=10, padx=10)

        # Dependencies
        ctk.CTkLabel(self.frame, text="Deps:").grid(row=14, column=0, sticky="nw", pady=10, padx=10)
        self.text_deps = ctk.CTkTextbox(self.frame, height=50)
        self.text_deps.grid(row=14, column=1, sticky="ew", pady=5, padx=10)

        # External Tools
        ctk.CTkLabel(self.frame, text="Tools:").grid(row=15, column=0, sticky="nw", pady=10, padx=10)
        self.text_tools = ctk.CTkTextbox(self.frame, height=50)
        self.text_tools.grid(row=15, column=1, sticky="ew", pady=5, padx=10)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_frame.grid(row=16, column=0, columnspan=3, pady=20, sticky="ew")
        
        ctk.CTkButton(btn_frame, text="Save", command=self.save).pack(side="right", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="transparent", border_width=1, command=self.destroy).pack(side="right", padx=10)
        
        if item_data:
            ctk.CTkButton(btn_frame, text="Delete Item", fg_color="#C0392B", hover_color="#E74C3C", 
                        command=self.delete).pack(side="left", padx=10)
            self.load_data(item_data)
            
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)

    def load_data(self, data):
        self.entry_name.insert(0, data.get('name', ''))
        self.combo_category.set(data.get('category', 'Custom'))
        self.entry_command.insert(0, data.get('command', ''))
        self.entry_icon.insert(0, data.get('icon', ''))
        self.entry_types.insert(0, data.get('types', '*'))
        self.combo_scope.set(data.get('scope', 'file'))
        self.combo_submenu.set(data.get('submenu', 'ContextUp'))
        self.entry_order.insert(0, str(data.get('order', 9999)))
        self.hk_var.set(data.get('hotkey', ''))
        self.enabled_var.set(data.get('enabled', True))
        self.gui_var.set(data.get('gui', True))
        self.tray_var.set(data.get('show_in_tray', False))
        self.combo_env.set(data.get('environment', 'system'))
        self.entry_desc.insert(0, data.get('description', ''))
        
        deps = data.get('dependencies', [])
        self.text_deps.insert("1.0", ", ".join(deps))
        
        tools = data.get('external_tools', [])
        self.text_tools.insert("1.0", ", ".join(tools))

    def browse_icon(self):
        path = tkinter.filedialog.askopenfilename(filetypes=[("Icon/Image", "*.ico *.png *.jpg")])
        if path:
            self.entry_icon.delete(0, "end")
            self.entry_icon.insert(0, path)

    def save(self):
        if not self.entry_name.get():
            messagebox.showwarning("Warning", "Name is required.")
            return

        deps_text = self.text_deps.get("1.0", "end").strip()
        deps = [d.strip() for d in deps_text.split(",") if d.strip()]
        
        tools_text = self.text_tools.get("1.0", "end").strip()
        tools = [t.strip() for t in tools_text.split(",") if t.strip()]

        new_item = {
            "id": self.item_data['id'] if self.item_data else str(time.time()).replace(".", ""),
            "name": self.entry_name.get(),
            "category": self.combo_category.get(),
            "command": self.entry_command.get(),
            "icon": self.entry_icon.get(),
            "types": self.entry_types.get(),
            "scope": self.combo_scope.get(),
            "submenu": self.combo_submenu.get(),
            "order": 9999,
            "hotkey": self.hk_var.get(),
            "enabled": self.enabled_var.get(),
            "gui": self.gui_var.get(),
            "show_in_tray": self.tray_var.get(),
            "environment": self.combo_env.get(),
            "description": self.entry_desc.get(),
            "dependencies": deps,
            "external_tools": tools
        }
        
        if self.on_save_callback:
            self.on_save_callback(new_item)
        self.destroy()


    def delete(self):
        if messagebox.askyesno("Confirm", "Delete this item?"):
            if self.on_delete_callback:
                self.on_delete_callback()
            self.destroy()

    def toggle_hotkey_recording(self):
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.btn_record.configure(text="Stop", fg_color="red")
            self.hk_var.set("Recording...")
            self.recorded_keys.clear()
            self.focus_force()
        else:
            self.btn_record.configure(text="Record", fg_color=["#3B8ED0", "#1F6AA5"])
            # Format keys
            parts = []
            if "<ctrl>" in self.recorded_keys: parts.append("Ctrl")
            if "<alt>" in self.recorded_keys: parts.append("Alt")
            if "<shift>" in self.recorded_keys: parts.append("Shift")
            if "<cmd>" in self.recorded_keys: parts.append("Win")
            
            # Find the non-modifier key
            for k in self.recorded_keys:
                if k not in ["<ctrl>", "<alt>", "<shift>", "<cmd>"]:
                    parts.append(k.upper())
            
            if parts:
                self.hk_var.set("+".join(parts))
            else:
                self.hk_var.set("")

    def on_key_press(self, event):
        if not self.is_recording: return
        key = event.keysym.lower()
        map_keys = {
            "control_l": "<ctrl>", "control_r": "<ctrl>",
            "alt_l": "<alt>", "alt_r": "<alt>",
            "shift_l": "<shift>", "shift_r": "<shift>",
            "super_l": "<cmd>", "super_r": "<cmd>"
        }
        formatted_key = map_keys.get(key, key)
        self.recorded_keys.add(formatted_key)

    def on_key_release(self, event):
        if not self.is_recording: return
        key = event.keysym.lower()
        map_keys = {
            "control_l": "<ctrl>", "control_r": "<ctrl>",
            "alt_l": "<alt>", "alt_r": "<alt>",
            "shift_l": "<shift>", "shift_r": "<shift>",
            "super_l": "<cmd>", "super_r": "<cmd>"
        }
        formatted_key = map_keys.get(key, key)
        if formatted_key in self.recorded_keys:
            self.recorded_keys.remove(formatted_key) 
