
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import math
from utils.gui_lib import PremiumScrollableFrame

# --- Design Tokens ---
class Colors:
    BG_MAIN = "#0F0F0F"       # Deep Void
    BG_CARD = "#1A1A1A"       # Surface
    BG_CARD_HOVER = "#252525"
    
    ACCENT_PRIMARY = "#00E676"   # Neon Mint
    THEME_ACCENT = "#0123B4"     # Royal Blue (Project Standard)
    ACCENT_SECONDARY = "#2979FF" # Electric Blue
    ACCENT_PURPLE = "#BB86FC"    # Magic/AI
    ACCENT_ERROR = "#FF5252"
    
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#B0BEC5"
    TEXT_TERTIARY = "#757575"
    
    BORDER_LIGHT = "#333333"
    BORDER_FOCUS = "#555555"

class Fonts:
    DISPLAY = ("Segoe UI Display", 24, "bold")
    HEADER = ("Segoe UI Display", 18, "bold")
    BODY = ("Segoe UI", 14)
    BODY_BOLD = ("Segoe UI", 14, "bold")
    SMALL = ("Segoe UI", 12)

# --- Custom Widgets ---

class GlassFrame(ctk.CTkFrame):
    """A frame with subtle border and specific background to mimic depth."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(
            fg_color=Colors.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER_LIGHT
        )

class PremiumLabel(ctk.CTkLabel):
    def __init__(self, master, style="body", **kwargs):
        font = Fonts.BODY
        text_color = Colors.TEXT_PRIMARY
        
        if style == "display":
            font = Fonts.DISPLAY
        elif style == "header":
            font = Fonts.HEADER
        elif style == "secondary":
            font = Fonts.BODY
            text_color = Colors.TEXT_SECONDARY
        elif style == "small":
            font = Fonts.SMALL
            text_color = Colors.TEXT_TERTIARY
            
        super().__init__(master, font=font, text_color=text_color, **kwargs)

class ActionButton(ctk.CTkButton):
    """Primary Action Button with glow effect simulation via color."""
    def __init__(self, master, variant="primary", **kwargs):
        super().__init__(master, **kwargs)
        self.configure(height=45, corner_radius=8, font=("Segoe UI", 14, "bold"))
        
        if variant == "primary":
            self.configure(
                fg_color=Colors.THEME_ACCENT,
                text_color="#FFFFFF",
                hover_color="#012fdf"
            )
        elif variant == "secondary":
            self.configure(
                fg_color="transparent",
                border_width=1,
                border_color=Colors.BORDER_LIGHT,
                text_color=Colors.TEXT_PRIMARY,
                hover_color=Colors.BG_CARD_HOVER
            )
        elif variant == "magic":
            self.configure(
                fg_color=Colors.ACCENT_SECONDARY,
                text_color="#FFFFFF",
                hover_color="#448AFF"
            )

class StatusBadge(ctk.CTkFrame):
    """Pill-shaped status indicator."""
    def __init__(self, master, text="Ready", status="neutral", **kwargs):
        super().__init__(master, height=28, corner_radius=14, **kwargs)
        
        # Color mapping
        colors = {
            "neutral": (Colors.BORDER_LIGHT, Colors.TEXT_SECONDARY),
            "success": ("#1B5E20", Colors.ACCENT_PRIMARY),
            "error": ("#B71C1C", Colors.ACCENT_ERROR),
            "active": ("#0D47A1", Colors.ACCENT_SECONDARY)
        }
        bg, fg = colors.get(status, colors["neutral"])
        
        self.configure(fg_color=bg)
        
        self.lbl = ctk.CTkLabel(self, text=text, text_color=fg, font=("Segoe UI", 11, "bold"))
        self.lbl.pack(padx=12, pady=4)
        
    def set_status(self, text, status="neutral"):
        colors = {
            "neutral": (Colors.BORDER_LIGHT, Colors.TEXT_SECONDARY),
            "success": ("#1B5E20", Colors.ACCENT_PRIMARY),
            "error": ("#B71C1C", Colors.ACCENT_ERROR),
            "active": ("#0D47A1", Colors.ACCENT_SECONDARY)
        }
        bg, fg = colors.get(status, colors["neutral"])
        self.configure(fg_color=bg)
        self.lbl.configure(text=text, text_color=fg)

# --- Base Window ---

from features.comfyui.base_gui import ComfyUIFeatureBase

class PremiumComfyWindow(ComfyUIFeatureBase):
    """
    Inherits logical core from ComfyUIFeatureBase but completely overrides the UI setup
    to enforce the Premium Design System.
    """
    def __init__(self, title, width=1200, height=800):
        super().__init__(title=title, width=width, height=height)
        
        # Override Theme - Apply to outer_frame to preserve root transparency
        if hasattr(self, 'outer_frame'):
            self.outer_frame.configure(fg_color=Colors.BG_MAIN)
        
        # Cleanup BaseWindow layout - remove default main_frame and status_frame
        # so we can build our own layout using pack
        if hasattr(self, 'main_frame'):
            self.main_frame.pack_forget()
            
        # Remove old status bar if exists (ComfyUIFeatureBase adds it)
        if hasattr(self, 'status_frame') and self.status_frame:
            self.status_frame.pack_forget()
            self.status_frame = None
            self.status_label_widget = None
            
        # --- Layout Structure using PACK (to match BaseWindow's outer_frame) ---
        self._build_header(title)
        self._build_content_area()
        
    def _build_header(self, title_text):
        self.header = ctk.CTkFrame(self.outer_frame, fg_color="transparent", height=60)
        self.header.pack(fill="x", padx=24, pady=(20, 10))
        
        # Title
        self.lbl_title = PremiumLabel(self.header, style="display", text=title_text)
        self.lbl_title.pack(side="left")
        
        # Connection Status (Right aligned)
        self.status_badge = StatusBadge(self.header, text="Connecting...", status="neutral")
        self.status_badge.pack(side="right")
        
    def _build_content_area(self):
        # Subclasses should put their content here
        # Adding pady=(0, 10) to ensure content doesn't hit the bottom rounded corners
        self.content_area = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True, padx=0, pady=(0, 10))
        # Default grid for content area
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)
        
    def _on_server_ready(self):
        """Override base handler to update new badge."""
        port = self.client.port
        self.status_badge.set_status(f"Engine Ready :{port}", "success")
        
    def _on_server_failed(self):
        """Override base handler."""
        self.status_badge.set_status(f"Engine Failed", "error")

