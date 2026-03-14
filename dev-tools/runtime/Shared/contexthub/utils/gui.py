import customtkinter as ctk
import tkinter as tk
from pathlib import Path
import sys

# Add src to path to import gui_lib
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.append(str(src_dir))

from .gui_lib import setup_theme

def ask_selection(title: str, prompt: str, options: list):
    """
    Shows a dialog with a combobox to select an option.
    Returns the selected string or None if cancelled.
    """
    # Ensure we have a root app for CTk
    root = None
    try:
        if ctk.CTk._root_window is None:
             root = ctk.CTk()
             root.withdraw()
    except:
        pass

    setup_theme()

    dialog = ctk.CTkToplevel()
    dialog.title(title)
    dialog.geometry("400x200")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    
    # Center the dialog
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"+{x}+{y}")
    
    dialog.focus_force()
    
    # Content
    ctk.CTkLabel(dialog, text=prompt, font=ctk.CTkFont(size=14)).pack(pady=(20, 10), padx=20)
    
    selection = ctk.StringVar()
    if options:
        selection.set(options[0])
        
    combo = ctk.CTkComboBox(dialog, variable=selection, values=options, state="readonly", width=250)
    combo.pack(pady=10, padx=20)
    
    result = None
    
    def on_ok():
        nonlocal result
        result = selection.get()
        dialog.destroy()
        
    def on_cancel():
        dialog.destroy()
        
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=20)
    
    ctk.CTkButton(btn_frame, text="OK", width=100, command=on_ok).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="Cancel", width=100, fg_color="transparent", border_width=1, border_color="gray", command=on_cancel).pack(side="left", padx=10)
    
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    dialog.bind('<Return>', lambda e: on_ok())
    dialog.bind('<Escape>', lambda e: on_cancel())
    
    dialog.wait_window()
    return result
