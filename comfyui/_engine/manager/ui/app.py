import customtkinter as ctk
import sys
import logging
from pathlib import Path
from tkinter import messagebox
import webbrowser

# Core
from manager.mgr_core.config import ConfigManager
from core.config import MenuConfig
from manager.mgr_core.packages import PackageManager
from manager.mgr_core.process import TrayProcessManager
from core.settings import load_settings, save_settings
from manager.mgr_core.updater import UpdateChecker
from core.registry import RegistryManager

# Resources
from manager.localization.translations import Translator

# UI Handles
from manager.ui.frames.editor import MenuEditorFrame
from manager.ui.frames.dashboard import DashboardFrame
from manager.ui.frames.dependencies import DependenciesFrame
from manager.ui.frames.categories import CategoriesFrame
from manager.ui.frames.logs import LogsFrame
from manager.ui.theme import Theme


class ContextUpManager(ctk.CTk):
    def __init__(self, root_dir: Path):
        super().__init__()
        self.root_dir = root_dir
        
        # Load Settings
        self.settings = load_settings()
        
        # Setup Translator
        self.tr = Translator(root_dir, self.settings.get("LANGUAGE", "en"))
        
        # Initialize Core Managers
        self.config_manager = ConfigManager(root_dir)
        self.package_manager = PackageManager(root_dir)
        self.process_manager = TrayProcessManager(root_dir, self.settings)
        
        # Registry needs MenuConfig (Lazy init now)
        self.registry_manager = None
        
        # Update checker
        self.update_checker = UpdateChecker(root_dir)
        self._update_available = False
        
        # Setup Window
        self.title("ContextUp Manager v3.0")
        self.geometry("1100x800")
        ctk.set_default_color_theme("dark-blue")
        
        # Apply saved theme preference
        saved_theme = self.settings.get("THEME", "Dark")
        ctk.set_appearance_mode(saved_theme)
        self.configure(fg_color=Theme.BG_MAIN)
        
        # Set window icon - single ContextUp icon for all
        self._set_app_icon()
        
        # --- Category Sync Logic ---
        # Defer sync to unblock startup
        # self._sync_categories()
        
        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self._create_sidebar()
        self._create_main_area()
        
        # Resize debounce for performance
        self._resize_timer = None
        self.bind("<Configure>", self._on_resize)
        
        # Lazy frame initialization - frames created on first access
        self.frames = {}
        self._frame_factories = {
            "editor": lambda: MenuEditorFrame(
                self.main_frame, 
                self.config_manager, 
                self.settings,
                self.package_manager,
                on_save_registry=self.apply_registry_changes,
                translator=self.tr
            ),
            "categories": lambda: CategoriesFrame(self.main_frame, self.settings, self.config_manager),
            # Pass config_manager to DashboardFrame to reuse cached config
            "dashboard": lambda: DashboardFrame(self.main_frame, self.settings, self.package_manager, self.config_manager, translator=self.tr, update_checker=self.update_checker),
            "dependencies": lambda: DependenciesFrame(
                self.main_frame, 
                self.settings, 
                self.package_manager,
                self.config_manager,
                translator=self.tr,
                root_dir=self.root_dir
            ),
            "logs": lambda: LogsFrame(self.main_frame, self.root_dir),
        }
        
        # Default View (Dashboard)
        self.show_frame("dashboard")
        
        # Post-Startup Tasks
        self.after(100, self._sync_categories) # Run sync after UI is shown
        self.after(1000, self._check_tray_status)
        
        # Auto-start Tray if enabled
        if self.settings.get("TRAY_ENABLED", False):
            self.after(2000, self._auto_start_tray)
        


    def _set_app_icon(self):
        """Set window icon and Windows taskbar icon."""
        try:
            # Set AppUserModelID for Windows Taskbar Icon grouping
            import ctypes
            myappid = 'hg.contextup.manager.3.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except:
            pass
        
        try:
            # Main ContextUp icon - single source of truth
            icon_path = self.root_dir / "assets" / "icons" / "ContextUp.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception as e:
            logging.warning(f"Failed to set app icon: {e}")
    
    def _on_resize(self, event):
        """Debounced resize handler to prevent layout thrashing."""
        # Only handle main window resize (not child widgets)
        if event.widget != self:
            return
        
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        
        # Delay layout update by 150ms
        self._resize_timer = self.after(150, self._on_resize_complete)
    
    def _on_resize_complete(self):
        """Called after resize debounce period."""
        self._resize_timer = None
        self.update_idletasks()

    def _auto_start_tray(self):
        if not self.process_manager.is_running():
            self.process_manager.start()
            self._update_tray_ui()

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=Theme.BG_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Spacer configuration to push Global Apply to bottom
        self.sidebar.grid_rowconfigure(10, weight=1)
        
        # Logo / Title
        ctk.CTkLabel(self.sidebar, text="ContextUp", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Nav Buttons
        self.nav_buttons = {}
        self.nav_badges = {}  # For update badge
        self._add_nav_btn(self.tr("manager.sidebar.dashboard"), "dashboard", 1) 
        self._add_nav_btn(self.tr("manager.sidebar.menu_editor"), "editor", 2)
        self._add_nav_btn(self.tr("manager.sidebar.categories"), "categories", 3)
        self._add_nav_btn(self.tr("manager.sidebar.dependencies"), "dependencies", 4)
        self._add_nav_btn(self.tr("manager.sidebar.logs"), "logs", 5)
        
        # Info Links (Sidebar Bottom)
        self._create_sidebar_info_links()
        
        # Sidebar Footer Area
        self.sidebar_footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_footer.grid(row=11, column=0, sticky="ews", padx=10, pady=20)
        
        # Tray Controls (Mini)
        self.tray_frame = ctk.CTkFrame(self.sidebar_footer, fg_color="transparent")
        self.tray_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(self.tray_frame, text=self.tr("manager.sidebar.tray_agent"), font=ctk.CTkFont(size=11, weight="bold"), text_color="gray60").pack(side="left")
        self.lbl_status = ctk.CTkLabel(self.tray_frame, text="● ...", text_color=Theme.TEXT_DIM, width=50, anchor="w")
        self.lbl_status.pack(side="left", padx=5)
        self.btn_tray = ctk.CTkButton(self.tray_frame, text="Start", width=50, height=22, 
                                     fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER,
                                     font=ctk.CTkFont(size=11, weight="bold"), command=self.toggle_tray_agent)
        self.btn_tray.pack(side="right")

        # GLOBAL APPLY BUTTON
        self.btn_apply = ctk.CTkButton(self.sidebar_footer, text=self.tr("manager.sidebar.apply_changes"), 
                                      height=40, 
                                      fg_color=Theme.PRIMARY, hover_color=Theme.PRIMARY_HOVER,
                                      font=ctk.CTkFont(size=14, weight="bold"),
                                      command=self.save_all_and_apply)
        self.btn_apply.pack(fill="x")

    def _create_sidebar_info_links(self):
        # Container in row 10 (which expands), aligned to bottom
        info_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        info_frame.grid(row=10, column=0, sticky="sew", padx=20, pady=(0, 5))
        
        ctk.CTkLabel(info_frame, text=self.tr("manager.dashboard.info.title"), 
                    font=ctk.CTkFont(size=12, weight="bold"), text_color="gray40").pack(anchor="w", pady=(0, 5))
        
        links = [
            (self.tr("manager.dashboard.info.documentation"), "https://github.com/simiroa/CONTEXTUP/blob/main/README_KR.md"),
            (self.tr("manager.dashboard.info.report_issue"), "https://github.com/simiroa/CONTEXTUP/issues"),
            (self.tr("manager.dashboard.info.community"), "#")
        ]
        
        for text, url in links:
            link = ctk.CTkButton(info_frame, text=text, fg_color="transparent", 
                               text_color=Theme.TEXT_DIM, hover=False, anchor="w", height=20,
                               font=ctk.CTkFont(size=11),
                               command=lambda u=url: webbrowser.open(u))
            link.pack(anchor="w", pady=0)

    def _add_nav_btn(self, text, name, row, show_badge=False):
        btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)
        
        btn = ctk.CTkButton(btn_frame, text=text, height=40, border_spacing=10, fg_color="transparent", 
                          text_color=Theme.TEXT_MAIN, hover_color=Theme.STANDARD_HOVER, anchor="w",
                          command=lambda n=name: self.show_frame(n))
        btn.grid(row=0, column=0, sticky="ew")
        self.nav_buttons[name] = btn
        
        # Add badge label if needed
        if show_badge:
            badge = ctk.CTkLabel(btn_frame, text="", width=20, font=ctk.CTkFont(size=10), 
                               fg_color=Theme.GRAY_BTN, corner_radius=10)
            badge.grid(row=0, column=1, padx=(0, 10))
            self.nav_badges[name] = badge

    def _create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=Theme.BG_MAIN, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

    def save_all_and_apply(self):
        """Global Save: Saves all tabs and updates registry."""
        try:
            # 1. Save all active frames
            for name, frame in self.frames.items():
                if hasattr(frame, 'save'):
                    try:
                        frame.save()
                    except Exception as e:
                        logging.error(f"Failed to save frame {name}: {e}")
                        
            # 2. Save Global Settings
            save_settings(self.settings)
            
            # 3. Apply Registry
            self.apply_registry_changes()
            
        except Exception as e:
            logging.error(f"Global Apply Failed: {e}")
            messagebox.showerror("Error", f"Failed to apply changes: {e}")

    def apply_registry_changes(self):
        """Cleanly re-apply all registry changes."""
        try:
            # 1. Initialize Registry Manager (Always recreate to ensure fresh settings/paths)
            try:
                # Reload MenuConfig and RegistryManager
                menu_config = MenuConfig()
                self.registry_manager = RegistryManager(menu_config)
            except Exception as e:
                logging.error(f"Failed to init RegistryManager: {e}")
                messagebox.showerror("Error", f"Failed to initialize Registry Manager: {e}")
                return

            # 2. Config is already loaded by MenuConfig() constructor usually, but ensure load.
            self.registry_manager.config.load() 

            # 3. Clean Cleanup
            self.registry_manager.unregister_all()
            
            # 4. Register
            self.registry_manager.register_all()
            
            # messagebox.showinfo("Success", "Registry updated successfully!") 
            # Changed to allow silent operation or consolidated message, but for now let's keep it visible or rely on save_all_and_apply
            # Since save_all_and_apply calls this, we might want to move the success message there.
            # But let's leave it here if it's called standalone? 
            # Actually, let's suppress it here and show it in save_all_and_apply if we want one big success.
            # For now, I'll log it and let save_all_and_apply confirm.
            logging.info("Registry updated successfully via Global Apply.")
            
            messagebox.showinfo("Success", "All changes saved and applied successfully!")
            
        except Exception as e:
            logging.error(f"Registry Update Failed: {e}")
            messagebox.showerror("Error", f"Failed to update registry: {e}")

    def _create_frame_lazy(self, name: str):
        """Create a frame on-demand (lazy initialization)."""
        if name in self._frame_factories:
            frame = self._frame_factories[name]()
            frame.grid(row=0, column=0, sticky="nsew")
            return frame
        return None

    def show_frame(self, name):
        # Lazy create frame if not exists
        if name not in self.frames:
            frame = self._create_frame_lazy(name)
            if frame:
                self.frames[name] = frame
                logging.info(f"Lazy-loaded frame: {name}")
        
        frame = self.frames.get(name)
        if frame:
            frame.tkraise()
            
            # Trigger on_visible callback if frame supports it (for deferred loading)
            if hasattr(frame, 'on_visible'):
                frame.on_visible()
            
            # Highlight button
            for n, btn in self.nav_buttons.items():
                if n == name:
                    btn.configure(fg_color=Theme.GRAY_BTN_HOVER)
                else:
                    btn.configure(fg_color="transparent")

    def toggle_tray_agent(self):
        running = self.process_manager.is_running()
        if running:
            success, msg = self.process_manager.stop()
            if not success:
                logging.warning(f"Failed to stop tray agent: {msg}")
            self.settings["TRAY_ENABLED"] = False
        else:
            success, msg = self.process_manager.start()
            if not success: messagebox.showerror("Error", msg)
            self.settings["TRAY_ENABLED"] = True
            
        save_settings(self.settings)
            
        self._update_tray_ui()
        
    def _check_tray_status(self):
        self._update_tray_ui()
        self.after(5000, self._check_tray_status) # Back to 5s for responsiveness



    def _update_tray_ui(self):
        running = self.process_manager.is_running()
        if running:
            self.lbl_status.configure(text="● Online", text_color=Theme.TEXT_SUCCESS)
            self.btn_tray.configure(text="Stop", fg_color=Theme.DANGER, hover_color=Theme.DANGER_HOVER)
        else:
            self.lbl_status.configure(text="● Offline", text_color=Theme.TEXT_DANGER)
            self.btn_tray.configure(text="Start", fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER)

    def _sync_categories(self):
        """Ensure all categories found in config are present in settings with a color and order."""
        try:
            items = self.config_manager.load_config()
            found_cats = set()
            for item in items:
                found_cats.add(item.get("category", "Uncategorized"))
                
            settings_cats = self.settings.setdefault("CATEGORY_COLORS", {})
            settings_order = self.settings.setdefault("CATEGORY_ORDER", [])
            
            changed = False
            
            # 1. Add missing colors
            defaults = ["#3498DB", "#E74C3C", "#2ECC71", "#F1C40F", "#9B59B6", "#1ABC9C", "#E67E22"]
            i = 0
            for cat in found_cats:
                if cat not in settings_cats:
                    settings_cats[cat] = defaults[i % len(defaults)]
                    i += 1
                    changed = True
                    
            # 2. Add missing order
            for cat in found_cats:
                if cat not in settings_order:
                    settings_order.append(cat)
                    changed = True
                    
            # 3. Clean up order (remove deleted cats? Maybe keep for robustness)
            # User can delete manually in Categories tab.
            
            if changed:
                save_settings(self.settings)
                
        except Exception as e:
            logging.error(f"Failed to sync categories: {e}")

    def refresh_app(self):
        """Reload configuration from disk and refresh UI and Registry."""
        try:
            # 1. Reload Config
            self.config_manager.load_config(force_reload=True)
            self._sync_categories()
            
            # 2. Refresh UI frames
            if "editor" in self.frames:
                self.frames["editor"].load_items()
               
            # 3. Re-apply Registry (Silent)
            # self.apply_registry_changes() # No, refresh shouldn't necessarily auto-apply registry unless user asks.
            # But the button says "Refresh", implying UI refresh.
            # If we want to reset registry too:
            # self.registry_manager.register_all()
            pass
            
        except Exception as e:
            logging.error(f"Refresh failed: {e}")
            messagebox.showerror("Error", f"Refresh failed: {e}")

    def save_app_settings(self):
        """Global save for settings.json"""
        try:
            save_settings(self.settings)
            # Re-init process manager settings in case python path changed
            self.process_manager.settings = self.settings 
            # messagebox.showinfo("Success", "Settings saved.") # Silent in global apply
            
            # Lazy Init Registry
            if self.registry_manager is None:
                try:
                    menu_config = MenuConfig()
                    self.registry_manager = RegistryManager(menu_config)
                except Exception as e:
                    logging.error(f"Failed to init RegistryManager: {e}")
            
            # Re-registry is handled by global apply now
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
