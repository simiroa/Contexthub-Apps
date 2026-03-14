import customtkinter as ctk
from pathlib import Path
import os
import sys

from core.settings import load_settings

# Standard Theme Settings
THEME_COLOR = "blue"

# Windows Creation Flags
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

def run_silent_command(cmd, **kwargs):
    """Run a subprocess silently (no window on Windows)."""
    import subprocess
    if 'creationflags' not in kwargs:
        kwargs['creationflags'] = CREATE_NO_WINDOW
    return subprocess.run(cmd, **kwargs)

# Theme Constants (Premium Dark)
THEME_BG = "#050505"        # Deep Black Background
THEME_CARD = "#121212"      # Slightly Brighter Cards (for contrast)
THEME_BORDER = "#1a1a1a"    # Visible Borders
THEME_ACCENT = "#0123B4"    # Unified Royal Blue
THEME_TEXT_MAIN = "#E0E0E0"
THEME_TEXT_DIM = "#666666"
# Unified Button Colors
THEME_BTN_PRIMARY = "#0123B4"  # Royal Blue - Main action buttons
THEME_BTN_HOVER = "#012fdf"    # Vibrant blue on hover
THEME_BTN_DANGER = "#C0392B"   # Red - Cancel/Delete/Destructive actions
THEME_BTN_DANGER_HOVER = "#E74C3C"  # Bright red on hover
THEME_BTN_SUCCESS = "#27AE60"  # Green - Confirm/Success actions
THEME_BTN_SUCCESS_HOVER = "#2ECC71"  # Bright green on hover
THEME_BTN_WARNING = "#D35400"  # Orange - Warning/Caution actions
THEME_BTN_WARNING_HOVER = "#E67E22"  # Bright orange on hover

# Unified Dropdown/ComboBox Colors (Toned Down)
THEME_DROPDOWN_FG = "#1a1a1a"    # Dark gray dropdown background (Subdued)
THEME_DROPDOWN_BTN = "#2a2a2a"   # Slightly lighter button area
THEME_DROPDOWN_HOVER = "#3a3a3a" # Hover state

# Global Theme Path
THEME_JSON = Path(__file__).parent / "theme_contextup.json"

TRANS_KEY = "#000001" # Transparency Key

def _resolve_repo_root():
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "Apps_installed").exists():
            return parent
    return current.parents[3]


def _log_gui_event(message: str):
    try:
        root = _resolve_repo_root()
        log_dir = root / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "gui_window.log"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass

def setup_theme():
    settings = load_settings()
    mode = settings.get("THEME", "System")
    if mode.lower() == "light": ctk.set_appearance_mode("Light")
    elif mode.lower() == "dark": ctk.set_appearance_mode("Dark")
    else: ctk.set_appearance_mode("System")

    if THEME_JSON.exists():
        ctk.set_default_color_theme(str(THEME_JSON))
    else:
        ctk.set_default_color_theme(THEME_COLOR)

    # Patch for border_spacing KeyError in some ctk versions
    try:
        # Ensure CTkScrollableFrame exists in theme (critical for FileListFrame)
        if "CTkScrollableFrame" not in ctk.ThemeManager.theme:
            ctk.ThemeManager.theme["CTkScrollableFrame"] = {
                "fg_color": ["#ffffff", "#121212"],
                "border_color": ["#e3e6e8", "#1a1a1a"],
                "border_width": 0,
                "border_spacing": 3,
                "corner_radius": 8,
                "label_fg_color": ["#f0f2f5", "#050505"]
            }

        # Global fix: Ensure border_spacing exists for ALL components in the theme
        for component in ctk.ThemeManager.theme:
            if isinstance(ctk.ThemeManager.theme[component], dict):
                    if "border_spacing" not in ctk.ThemeManager.theme[component]:
                        # Scrollable frame usually needs ~3, others 0
                        default_space = 3 if "Scrollable" in component else 0
                        ctk.ThemeManager.theme[component]["border_spacing"] = default_space

                    # Ensure scrollbar colors exist (Crucial for CTk 5.x)
                    if "scrollbar_button_color" not in ctk.ThemeManager.theme[component]:
                        ctk.ThemeManager.theme[component]["scrollbar_button_color"] = ["#a0a0a0", "#3a3a3a"]
                    if "scrollbar_button_hover_color" not in ctk.ThemeManager.theme[component]:
                        ctk.ThemeManager.theme[component]["scrollbar_button_hover_color"] = ["#808080", "#4a4a4a"]
    except Exception as e:
        print(f"Theme patch failed: {e}")

class BaseWindow(ctk.CTk):
    """
    Base window class for all ContextUp tools.
    Provides standard premium styling, geometry, custom title bar, and icon handling.
    """
    def __init__(self, title="ContextUp Tool", width=700, height=750, scrollable=False, icon_name=None):
        super().__init__()
        setup_theme()

        # 0. Decentralized I18n Loading
        self._setup_locales()

        from .i18n import t
        self.tool_title = t(title)
        _log_gui_event(f"BaseWindow init title_in={title} title_out={self.tool_title} size={width}x{height}")

        # Borderless Window Setup
        self.overrideredirect(True)
        self.wm_attributes("-transparentcolor", TRANS_KEY)
        self.configure(fg_color=TRANS_KEY)

        self._offsetx = 0
        self._offsety = 0

        # Main Outer Container (Rounded Border)
        # Increased margin to 10 to ensure radius 16 isn't clipped by root window bounds
        self.outer_frame = ctk.CTkFrame(self, fg_color=THEME_BG, corner_radius=16,
                                      border_width=1, border_color=THEME_BORDER)
        self.outer_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Custom Title Bar
        self.title_bar = ctk.CTkFrame(self.outer_frame, fg_color="transparent", height=40, corner_radius=0)
        self.title_bar.pack(fill="x", side="top", padx=10, pady=(5, 0))

        # Icon/Title
        self.title_label = ctk.CTkLabel(self.title_bar, text=f"✨ {self.tool_title}", font=("Segoe UI", 12, "bold"), text_color=THEME_TEXT_MAIN)
        self.title_label.pack(side="left", padx=5)

        # Window Controls
        ctrl_frame = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        ctrl_frame.pack(side="right")

        self.btn_min = ctk.CTkButton(ctrl_frame, text="─", width=32, height=28,
                                   fg_color="transparent", hover_color="#222",
                                   command=self.minimize_window, font=("Arial", 11), corner_radius=6)
        self.btn_min.pack(side="left", padx=2)

        self.btn_close = ctk.CTkButton(ctrl_frame, text="✕", width=32, height=28,
                                     fg_color="transparent", hover_color="#922B21",
                                     command=self.on_closing, font=("Arial", 11), corner_radius=6)
        self.btn_close.pack(side="left", padx=2)

        # Drag Logic
        for w in [self.title_bar, self.title_label, ctrl_frame]:
            w.bind("<Button-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)

        # Set geometry logic handling
        self.geometry(f"{width}x{height}")

        # Taskbar Logic
        self._setup_taskbar_icon(icon_name)

        # Ensure the window is visible and focused (context menu launches can hide it)
        self.after(50, self._ensure_visible)

        # Content Area
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # Outer frame handled by pack

        # We need to structure internal content.
        # BaseWindow typically expects self.main_frame to be ready for children.

        # Footer Area (always at bottom)
        self.footer_frame = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        self.footer_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        container_args = {"fg_color": "transparent"}
        if scrollable:
            self.main_frame = ctk.CTkScrollableFrame(self.outer_frame, **container_args)
        else:
            self.main_frame = ctk.CTkFrame(self.outer_frame, **container_args)

        self.main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Failsafe for capture mode: automatically close after 60s
        if os.environ.get("CTX_CAPTURE_MODE") == "1":
            _log_gui_event(f"BaseWindow: Capture mode detected. Scheduling auto-close in 60s.")
            self.after(60000, self.destroy)

    def _setup_locales(self):
        """Automatically load locales.json from app root or its parents."""
        try:
            from .i18n import load_extra_strings
            app_root = os.environ.get("CTX_APP_ROOT")
            if not app_root:
                # Try to resolve from entry point or current file
                try:
                    app_root = str(Path(sys.argv[0]).resolve().parent)
                except:
                    app_root = str(Path.cwd())

            if app_root:
                root_path = Path(app_root)
                _log_gui_event(f"BaseWindow: Searching for locales in {root_path}")

                # We want to load multiple locales if found (prioritizing engine)
                # Search order: root -> parents -> _engine
                search_paths = []

                # 1. Check root and up to 3 parent levels
                curr = root_path
                for _ in range(3):
                    search_paths.append(curr)
                    # Also check _engine sibling/child
                    if (curr / "_engine").exists():
                        search_paths.append(curr / "_engine")
                    if curr.parent == curr: break
                    curr = curr.parent

                # Load found locales (Duplicates will be merged in i18n module)
                loaded_any = False
                for p in reversed(search_paths): # Load from top-level down so locals override globals (if desired)
                    for name in ["locales.json", "translations.json"]:
                        loc_path = p / name
                        if loc_path.exists():
                            _log_gui_event(f"BaseWindow: Loading locales from {loc_path}")
                            load_extra_strings(loc_path)
                            loaded_any = True

                if not loaded_any:
                    _log_gui_event("BaseWindow: No extra locales found.")
        except Exception as e:
            _log_gui_event(f"BaseWindow I18n failed: {e}")
            print(f"BaseWindow I18n failed: {e}")

    def _setup_taskbar_icon(self, icon_name):
        # Set AppUserModelID
        try:
            import ctypes
            myappid = 'hg.contextup.tool.2.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except: pass

    def _ensure_visible(self):
        try:
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.update_idletasks()
            self.focus_force()
            self.after(200, lambda: self.attributes("-topmost", False))
            _log_gui_event("BaseWindow ensure_visible executed")
        except Exception:
            pass

        app_root = os.environ.get("CTX_APP_ROOT")
        icon_path = None

        try:
            if app_root:
                app_root_path = Path(app_root)
                if icon_name:
                    icon_named = app_root_path / f"icon_{icon_name}.ico"
                    if icon_named.exists():
                        icon_path = icon_named
                    else:
                        icon_named_png = app_root_path / f"icon_{icon_name}.png"
                        if icon_named_png.exists():
                            icon_path = icon_named_png

                if not icon_path:
                    for candidate in ["icon.ico", "icon.png", "preview.png"]:
                        candidate_path = app_root_path / candidate
                        if candidate_path.exists():
                            icon_path = candidate_path
                            break

            if icon_path:
                if str(icon_path).lower().endswith(".png"):
                    try:
                        from tkinter import PhotoImage
                        self.iconphoto(True, PhotoImage(file=str(icon_path)))
                    except: pass
                else:
                    self.iconbitmap(icon_path)
        except: pass

    def start_move(self, event):
        self._offsetx = event.x
        self._offsety = event.y

    def do_move(self, event):
        x = self.winfo_x() + event.x - self._offsetx
        y = self.winfo_y() + event.y - self._offsety
        self.geometry(f"+{x}+{y}")

    def minimize_window(self):
        self.update_idletasks()
        self.withdraw()
        self.after(10, self.iconify)
        self.bind("<Map>", lambda e: self.deiconify())

    def on_closing(self):
        self.destroy() # Defaults, can be overridden

    def adjust_window_size(self):
        """Auto-adjust window size to perfectly fit its content."""
        self.update_idletasks()

        try:
            # 1. Calculate Required Height
            # If scrollable, we attempt to get the inner content height
            if isinstance(self.main_frame, ctk.CTkScrollableFrame):
                # Accessory to CTkScrollableFrame internals for accurate content height
                try:
                    content_h = self.main_frame._inner_frame.winfo_reqheight()
                except:
                    content_h = self.main_frame.winfo_reqheight()
            else:
                content_h = self.main_frame.winfo_reqheight()

            title_h = self.title_bar.winfo_reqheight()
            footer_h = self.footer_frame.winfo_reqheight()

            # Sum components + padding/margins
            # We add a bit of safety padding for the outer container and spacing
            total_h = content_h + title_h + footer_h + 35

            # 2. Calculate Required Width
            # Usually we use a standard width, but we can check content
            req_w = self.main_frame.winfo_reqwidth()
            width = max(600, req_w)
            if width > 1000: width = 1000 # Limit max width

            # 3. Screen Constraints
            screen_h = self.winfo_screenheight()
            screen_w = self.winfo_screenwidth()

            max_h = int(screen_h * 0.9)
            if total_h > max_h:
                total_h = max_h
                # If content is larger than 90% screen, scrolling will stay if enabled

            if total_h < 300: total_h = 300

            # Apply geometry centered (optional, but keep simple for now)
            self.geometry(f"{width}x{total_h}")

            # Trigger one last update to ensure layout settles
            self.update_idletasks()

        except Exception as e:
            _log_gui_event(f"adjust_window_size error: {e}")
            _log_gui_event(f"adjust_window_size error: {e}")
            # Fallback
            self.geometry("600x500")

    def add_header(self, text, font_size=18):
        """Adds a standard header label."""
        label = ctk.CTkLabel(self.main_frame, text=text, text_color=THEME_TEXT_MAIN,
                           font=ctk.CTkFont(size=font_size, weight="bold"))
        label.pack(anchor="w", padx=10, pady=(10, 15))
        return label

    def add_section(self, title):
        """Adds a section title."""
        label = ctk.CTkLabel(self.main_frame, text=title, text_color=THEME_ACCENT,
                           font=ctk.CTkFont(size=13, weight="bold"))
        label.pack(anchor="w", padx=10, pady=(10, 5))
        return label

    def create_card_frame(self, parent=None):
        """Creates a standardized card frame."""
        if parent is None: parent = self.main_frame
        return ctk.CTkFrame(parent, fg_color=THEME_CARD, corner_radius=12,
                          border_width=1, border_color=THEME_BORDER)

class FileListFrame(ctk.CTkScrollableFrame):
    """
    Standard scrollable list for displaying selected files.
    """
    def __init__(self, master, files, height=150):
        super().__init__(master, height=height, fg_color="transparent") # Transparent background
        self.files = files
        self.populate()

    def populate(self):
        for widget in self.winfo_children():
            widget.destroy()

        for f in self.files:
            row = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=6)
            row.pack(fill="x", pady=2)

            # Icon based on extension
            icon = "📄"
            if f.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv']: icon = "🎥"
            elif f.suffix.lower() in ['.mp3', '.wav', '.flac']: icon = "🎵"
            elif f.suffix.lower() in ['.jpg', '.png', '.exr']: icon = "🖼️"

            ctk.CTkLabel(row, text=icon, width=30, text_color=THEME_TEXT_DIM).pack(side="left")
            ctk.CTkLabel(row, text=f.name, anchor="w", text_color=THEME_TEXT_MAIN).pack(side="left", fill="x", expand=True)

            size_str = "0.0 KB"
            if f.exists():
                size_str = self.format_size(f.stat().st_size)
            ctk.CTkLabel(row, text=size_str, text_color=THEME_TEXT_DIM, width=80).pack(side="right")

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024: return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

class PremiumScrollableFrame(ctk.CTkScrollableFrame):
    """
    A premium scrollable frame that automatically hides its scrollbars
    when the content fits within the visible area.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Wrap the canvas scroll commands to handle visibility
        if hasattr(self, "_scrollbar"):
            self._parent_canvas.configure(yscrollcommand=self._dynamic_set_y)
        if hasattr(self, "_h_scrollbar"):
            self._parent_canvas.configure(xscrollcommand=self._dynamic_set_x)

    def _dynamic_set_y(self, low, high):
        try:
            if float(low) <= 0.0 and float(high) >= 1.0:
                self._scrollbar.grid_remove()
            else:
                self._scrollbar.grid()
        except: pass
        self._scrollbar.set(low, high)

    def _dynamic_set_x(self, low, high):
        try:
            if float(low) <= 0.0 and float(high) >= 1.0:
                self._h_scrollbar.grid_remove()
            else:
                self._h_scrollbar.grid()
        except: pass
        self._h_scrollbar.set(low, high)

class ModernInputDialog(ctk.CTkToplevel):
    """
    A modern replacement for simpledialog.askstring using CustomTkinter.
    """
    def __init__(self, title="Input", text="Enter value:", initial_value=""):
        super().__init__()
        setup_theme()

        # Premium styling for Dialog
        self.overrideredirect(True)
        self.wm_attributes("-transparentcolor", TRANS_KEY)
        self.configure(fg_color=TRANS_KEY)

        # Center on screen
        self.update_idletasks()
        width = 400
        height = 180
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

        # Frame
        self.outer_frame = ctk.CTkFrame(self, fg_color=THEME_BG, corner_radius=16,
                                      border_width=1, border_color=THEME_ACCENT)
        self.outer_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.result = None

        # Header
        ctk.CTkLabel(self.outer_frame, text=title, font=("Segoe UI", 12, "bold"), text_color=THEME_TEXT_MAIN).pack(pady=(15, 5))

        ctk.CTkLabel(self.outer_frame, text=text, font=("Segoe UI", 11), text_color=THEME_TEXT_MAIN).pack(anchor="w", padx=20, pady=(5, 5))

        self.entry = ctk.CTkEntry(self.outer_frame, fg_color=THEME_CARD, border_color=THEME_BORDER, text_color=THEME_TEXT_MAIN)
        self.entry.pack(fill="x", padx=20, pady=(0, 15))
        if initial_value:
            self.entry.insert(0, initial_value)
        self.entry.bind("<Return>", self.on_ok)
        self.entry.focus_force()

        btn_frame = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(btn_frame, text="OK", width=80, height=32, command=self.on_ok,
                    fg_color=THEME_ACCENT).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", width=80, height=32, command=self.on_cancel,
                    fg_color="transparent", border_width=1, border_color=THEME_BORDER, hover_color="#333").pack(side="right", padx=5)

        self.wait_visibility()
        self.grab_set()
        self.wait_window()

    def on_ok(self, event=None):
        self.result = self.entry.get()
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

def ask_string_modern(title, text, initial_value=""):
    # Check if a root window exists
    try:
        if not ctk._default_root_arg:
            root = ctk.CTk()
            root.withdraw() # Hide it
        else:
            root = None
    except:
        root = ctk.CTk()
        root.withdraw()

    app = ModernInputDialog(title, text, initial_value)
    result = app.result

    if root:
        root.destroy()

    return result

class MissingDependencyWindow(BaseWindow):
    """
    A specific window to show when a tool cannot run due to missing dependencies.
    """
    def __init__(self, tool_name, missing_items):
        super().__init__(title=f"Missing Requirements - {tool_name}", width=500, height=400)

        # Icon (Error/Warning)
        self.lbl_icon = ctk.CTkLabel(self.main_frame, text="⚠️", font=("Segoe UI Emoji", 64))
        self.lbl_icon.pack(pady=(20, 10))

        self.add_header(f"{tool_name} Unavailable", font_size=24)

        msg = f"This feature requires external tools that are not currently installed or connected."
        ctk.CTkLabel(self.main_frame, text=msg, wraplength=400, justify="center", text_color=THEME_TEXT_DIM).pack(pady=(0, 20))

        # Missing List using Card style
        bg_frame = self.create_card_frame(self.main_frame)
        bg_frame.pack(fill="x", padx=40, pady=10)

        ctk.CTkLabel(bg_frame, text="Missing Components:", font=("Segoe UI", 12, "bold"), text_color=THEME_TEXT_MAIN).pack(anchor="w", padx=15, pady=(10,0))

        for item in missing_items:
            ctk.CTkLabel(bg_frame, text=f"• {item}", anchor="w", text_color="#ff5555").pack(anchor="w", padx=25, pady=2)

        ctk.CTkLabel(bg_frame, text="").pack(pady=5) # Spacer

        # Action Arguments
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        # Open Manager Button
        ctk.CTkButton(btn_frame, text="Open Manager", command=self.open_manager, fg_color="#2cc985", hover_color="#22a36b").pack(side="top", pady=5)

        # Close
        ctk.CTkButton(btn_frame, text="Close", command=self.destroy, fg_color="transparent", border_width=1, border_color=THEME_BORDER).pack(side="top", pady=5)

    def open_manager(self):
        """Attempts to launch the Manager."""
        try:
            # We assume manage.py is in the root
            root = Path(__file__).resolve().parents[3]
            manage_script = root / "manage.py"
            if manage_script.exists():
                import subprocess
                subprocess.Popen([sys.executable, str(manage_script)])
                self.destroy()
        except Exception as e:
            print(f"Failed to open manager: {e}")

class ModelManagerFrame(ctk.CTkFrame):
    """
    Standard UI for checking and downloading AI models.
    """
    def __init__(self, master, model_name, model_dir, download_command=None, check_callback=None, **kwargs):
        super().__init__(master, fg_color=THEME_CARD, corner_radius=12, border_width=1, border_color=THEME_BORDER, **kwargs)

        self.model_name = model_name
        self.model_dir = Path(model_dir) if model_dir else None
        self.download_command = download_command
        self.check_callback = check_callback

        # Layout
        self.grid_columnconfigure(1, weight=1)

        # Icon
        self.lbl_icon = ctk.CTkLabel(self, text="📦", font=("Segoe UI Emoji", 20))
        self.lbl_icon.grid(row=0, column=0, rowspan=2, padx=(10, 6), pady=(10, 6), sticky="n")

        # Title
        self.lbl_title = ctk.CTkLabel(self, text=f"{model_name} Model", font=("Segoe UI", 12, "bold"), text_color=THEME_TEXT_MAIN)
        self.lbl_title.configure(anchor="w", justify="left")
        self.lbl_title.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(10, 0))

        # Status Text
        self.lbl_status = ctk.CTkLabel(self, text="Checking...", font=("Segoe UI", 11), text_color=THEME_TEXT_DIM)
        self.lbl_status.configure(anchor="w", justify="left")
        self.lbl_status.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 8))

        # Action Button
        self.btn_action = ctk.CTkButton(self, text="Check", width=80, height=28,
                                      font=("Segoe UI", 11), fg_color=THEME_BTN_PRIMARY,
                                      command=self.on_action)
        self.btn_action.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        self.bind("<Configure>", self._handle_resize)

        self.check_status()

    def _handle_resize(self, event=None):
        try:
            wrap_width = max(140, self.winfo_width() - 90)
            self.lbl_title.configure(wraplength=wrap_width)
            self.lbl_status.configure(wraplength=wrap_width)
        except Exception:
            pass

    def check_status(self):
        """Checks if model directory exists and has files or a custom callback passes."""
        is_installed = False
        if self.check_callback:
            try:
                is_installed = bool(self.check_callback())
            except Exception:
                is_installed = False
        if not is_installed and self.model_dir and self.model_dir.exists() and any(self.model_dir.iterdir()):
            is_installed = True

        if is_installed:
            self.lbl_status.configure(text="Installed", text_color=THEME_BTN_SUCCESS)
            self.btn_action.configure(text="Re-Check", fg_color="transparent", border_width=1, border_color=THEME_BORDER)
            return True
        else:
            self.lbl_status.configure(text="Not Installed", text_color="#E74C3C")
            self.btn_action.configure(text="Download", fg_color=THEME_BTN_PRIMARY)
            return False

    def on_action(self):
        if self.download_command:
            self.download_command()
        else:
            self.check_status()
