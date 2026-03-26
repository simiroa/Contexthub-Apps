"""
AI-powered background removal using the Qt app entrypoint.
"""
from tkinter import messagebox
from utils.i18n import t

from features.ai.bg_removal_qt_app import start_app as start_background_removal

def remove_background(target_path: str):
    """Launch the background removal Qt app for the given target."""
    try:
        start_background_removal([str(target_path)])
    except Exception as e:
        messagebox.showerror(t("common.error"), t("ai_common.failed").format(error=e))
