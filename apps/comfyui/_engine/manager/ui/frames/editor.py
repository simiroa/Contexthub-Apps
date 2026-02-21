import customtkinter as ctk
import tkinter.messagebox
from tkinter import Menu
from manager.ui.dialogs.item_editor import ItemEditorDialog
from manager.ui.dialogs.manual_viewer import ManualViewerDialog
from manager.helpers.icons import IconManager
from manager.helpers.requirements import RequirementHelper
from manager.ui.theme import Theme

class MenuEditorFrame(ctk.CTkFrame):
    def __init__(self, parent, config_manager, settings, package_manager, on_save_registry=None, translator=None):
        super().__init__(parent, fg_color="transparent")
        self.config_manager = config_manager
        self.settings = settings
        self.package_manager = package_manager
        self.on_save_registry = on_save_registry
        self.tr = translator if translator else lambda k: k
        
        self.items = [] 
        self.filtered_items = []
        self.item_vars = {} # {id: BooleanVar}
        self.row_widgets = {} # {id: widget}
        self.view_mode = "Grouped" # Grouped | Flat
        
        # Cache for performance
        self.installed_packages = self.package_manager.get_installed_packages()
        self.requirements = RequirementHelper(self.config_manager.root_dir, self.package_manager)
        
        # Widget pooling for performance
        self._row_pool = []  # List of reusable row widgets
        self._header_pool = []  # List of reusable header widgets
        self._active_rows = []  # Currently visible rows
        self._active_headers = []  # Currently visible headers
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) 
        
        self._setup_toolbar()
        self._setup_filters()
        self._setup_list()
        
        # Initial Load
        self.load_items()

    def load_items(self):
        self.items = self.config_manager.load_config()
        self.refresh_list()

    def _open_dependencies(self):
        root = self.winfo_toplevel()
        if hasattr(root, "show_frame"):
            root.show_frame("dependencies")

    def _format_requirements_text(self, missing_packages, missing_models):
        lines = []
        if missing_packages:
            lines.append("Packages: " + ", ".join(sorted(missing_packages)))
        if missing_models:
            lines.append("Models: " + ", ".join(sorted(missing_models)))
        return "\n".join(lines)

    def _set_switch_state(self, switch, var, state):
        switch._busy = True
        var.set(state)
        switch._busy = False

    def _on_item_toggle(self, item, enabled_var, switch):
        if getattr(switch, "_busy", False):
            return

        new_state = bool(enabled_var.get())
        if not new_state:
            item["enabled"] = False
            return

        missing_tools = self.requirements.get_missing_external_tools(item.get("external_tools", []))
        if missing_tools:
            msg = self.tr("manager.frames.editor.requirements_external_tools").format(
                tools=", ".join(sorted(missing_tools))
            )
            if tkinter.messagebox.askyesno(self.tr("manager.frames.editor.requirements_title"), msg):
                self._open_dependencies()
            self._set_switch_state(switch, enabled_var, False)
            item["enabled"] = False
            return

        missing_packages = self.requirements.get_missing_packages(
            item.get("dependencies", []),
            installed_packages=self.installed_packages
        )
        missing_models = self.requirements.get_missing_models_for_item(item)

        if not missing_packages and not missing_models:
            item["enabled"] = True
            return

        requirements_text = self._format_requirements_text(missing_packages, missing_models)
        prompt = self.tr("manager.frames.editor.requirements_install_prompt").format(
            requirements=requirements_text
        )
        if not tkinter.messagebox.askyesno(self.tr("manager.frames.editor.requirements_title"), prompt):
            self._set_switch_state(switch, enabled_var, False)
            item["enabled"] = False
            return

        switch.configure(state="disabled")

        def finalize(success):
            def update_ui():
                switch.configure(state="normal")
                self.installed_packages = self.package_manager.get_installed_packages()
                self.refresh_list()
                if success:
                    item["enabled"] = True
                    self._set_switch_state(switch, enabled_var, True)
                    tkinter.messagebox.showinfo(
                        self.tr("manager.frames.editor.requirements_title"),
                        self.tr("manager.frames.editor.requirements_install_success")
                    )
                else:
                    item["enabled"] = False
                    self._set_switch_state(switch, enabled_var, False)
                    tkinter.messagebox.showerror(
                        self.tr("manager.frames.editor.requirements_title"),
                        self.tr("manager.frames.editor.requirements_install_failed")
                    )

            self.after(0, update_ui)

        def on_models_complete(results):
            models_ok = all(results.values()) if results else True
            finalize(models_ok)

        def on_packages_complete(success):
            if not success:
                finalize(False)
                return
            if missing_models:
                self.requirements.install_models_async(missing_models, completion_callback=on_models_complete)
            else:
                finalize(True)

        if missing_packages:
            dep_meta = self.requirements.build_dep_metadata(missing_packages)
            self.package_manager.install_packages(missing_packages, dep_meta, completion_callback=on_packages_complete)
        elif missing_models:
            self.requirements.install_models_async(missing_models, completion_callback=on_models_complete)

    def _setup_toolbar(self):
        toolbar = ctk.CTkFrame(self, height=40, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=20, pady=(10,0))
        
        # Left: Bulk Actions
        ctk.CTkButton(toolbar, text="Select All", width=70, fg_color=Theme.STANDARD, 
                     hover_color=Theme.STANDARD_HOVER, command=self.select_all).pack(side="left", padx=5, pady=5)
        
        # Bulk Menu (Move/Toggle)
        self.btn_bulk = ctk.CTkButton(toolbar, text="Bulk Action ▼", width=100, 
                                     fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER,
                                     command=self.show_bulk_menu)
        self.btn_bulk.pack(side="left", padx=5, pady=5)
        
        # Refresh Menu (next to Bulk Action)
        ctk.CTkButton(toolbar, text="⟳ Refresh", width=80, fg_color=Theme.GRAY_BTN, 
                     hover_color=Theme.GRAY_BTN_HOVER,
                     command=self._refresh_from_disk).pack(side="left", padx=5, pady=5)
        
        # Right: Core Actions
        ctk.CTkButton(toolbar, text=self.tr("common.refresh"), width=80, fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER, 
                    command=self.load_items).pack(side="right", padx=5, pady=5)
        ctk.CTkButton(toolbar, text="Auto Organize", width=100, fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER, 
                command=self.auto_organize).pack(side="right", padx=5, pady=5)
        ctk.CTkButton(toolbar, text="+ Add Item", fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER, width=90,
                command=self.open_add_dialog).pack(side="right", padx=10, pady=5)
    
    def _refresh_from_disk(self):
        """Reload config from disk and refresh list."""
        self.config_manager.load_config(force_reload=True)
        # Refresh packages cache
        self.installed_packages = self.package_manager.get_installed_packages()
        self.load_items()
        tkinter.messagebox.showinfo("Refreshed", "Menu configuration reloaded from disk.")


    def _setup_filters(self):
        filter_frame = ctk.CTkFrame(self, height=40, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(5,0))
        
        # View Mode Toggle
        self.btn_view = ctk.CTkButton(filter_frame, text=f"View: {self.view_mode}", width=100, 
                                     fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER, 
                                     command=self.toggle_view)
        self.btn_view.pack(side="left", padx=5)

        ctk.CTkLabel(filter_frame, text="Filter:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(15, 5))
        
        # Categories (Only relevant in Flat view mostly, but keep for search)
        self.filter_cat_var = ctk.StringVar(value="All Categories")
        # Populate later based on settings
        
        self.entry_search = ctk.CTkEntry(filter_frame, placeholder_text="Search Name...", width=150)
        self.entry_search.pack(side="left", padx=5)
        self.entry_search.bind("<Return>", self.refresh_list)
        
        ctk.CTkButton(filter_frame, text="🔍", width=30, 
                     fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER,
                     command=self.refresh_list).pack(side="left", padx=2)
        # Renamed to Clear to avoid confusion with 'Reset Settings'
        ctk.CTkButton(filter_frame, text="✖", width=30, fg_color=Theme.STANDARD, 
                     hover_color=Theme.STANDARD_HOVER, command=self.reset_filters).pack(side="left", padx=5)

    def _setup_list(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Menu Items", fg_color=Theme.BG_MAIN)
        self.scroll_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

    def toggle_view(self):
        self.view_mode = "Flat" if self.view_mode == "Grouped" else "Grouped"
        self.btn_view.configure(text=f"View: {self.view_mode}")
        self.refresh_list()

    def reset_filters(self):
        self.entry_search.delete(0, "end")
        self.item_vars.clear() # Also clear selection? User might expect this.
        self.refresh_list()
        
    def show_bulk_menu(self):
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Select All", command=self.select_all)
        menu.add_command(label="Deselect All", command=self.deselect_all)
        menu.add_separator()
        menu.add_command(label="Enable Selected", command=lambda: self.bulk_toggle(True, selected_only=True))
        menu.add_command(label="Disable Selected", command=lambda: self.bulk_toggle(False, selected_only=True))
        menu.add_separator()
        menu.add_command(label="Enable All (Except Beta)", command=lambda: self.bulk_toggle(True, beta_filter=True))
        menu.add_command(label="Disable All", command=lambda: self.bulk_toggle(False))
        menu.add_separator()
        
        # Move to Category Submenu
        move_menu = Menu(menu, tearoff=0)
        cats = sorted(self.settings.get("CATEGORY_COLORS", {}).keys())
        for cat in cats:
            move_menu.add_command(label=cat, command=lambda c=cat: self.bulk_move(c))
        
        menu.add_cascade(label="Move Selected to...", menu=move_menu)
        
        try:
            menu.tk_popup(self.btn_bulk.winfo_rootx(), self.btn_bulk.winfo_rooty() + self.btn_bulk.winfo_height())
        finally:
            menu.grab_release()

    def select_all(self):
        for v in self.item_vars.values(): v.set(True)

    def deselect_all(self):
        for v in self.item_vars.values(): v.set(False)

    def bulk_toggle(self, state, selected_only=False, beta_filter=False):
        changed = False
        target_items = self.filtered_items if self.filtered_items else self.items
        
        for item in target_items:
            # Check Selection
            if selected_only:
                var = self.item_vars.get(item['id'])
                if not var or not var.get():
                    continue
            
            # Check Beta
            if beta_filter:
                # Assuming 'Beta' is in name or status
                name = item.get('name', '').lower()
                status = item.get('status', '').lower() # Assuming 'status' field might be used
                if 'beta' in name or 'beta' in status:
                    # If enabling except beta, skip this
                    if state: continue 
                    
            if item.get('enabled', True) != state:
                item['enabled'] = state
                changed = True
                
        if changed:
            self.refresh_list()
            # self.save_final() # Optional: Auto-save? Better to let user click save.
            tkinter.messagebox.showinfo("Bulk Action", "Status updated. Click 'Save Changes' to apply.")

    def bulk_move(self, category):
        changed = False
        target_items = self.filtered_items if self.filtered_items else self.items
        
        for item in target_items:
            var = self.item_vars.get(item['id'])
            if var and var.get():
                if item.get('category') != category:
                    item['category'] = category
                    changed = True
                    
        if changed:
            self.recalculate_orders()
            self.refresh_list()
            tkinter.messagebox.showinfo("Bulk Move", f"Moved selected items to '{category}'.")
    
    # Removed duplicate select_all which was below

    def refresh_list(self, _=None):
        # Freeze scroll frame during rebuild
        self.scroll_frame.grid_remove()
        
        # Return active rows/headers to pool (hide, don't destroy)
        for row in self._active_rows:
            row.pack_forget()
            self._row_pool.append(row)
        for header in self._active_headers:
            header.pack_forget()
            self._header_pool.append(header)
        
        self._active_rows = []
        self._active_headers = []
        self.item_vars.clear()
        self.row_widgets.clear()
        
        search = self.entry_search.get().lower()
        
        # Filter
        filtered = []
        for item in self.items:
            if search and search not in item.get('name', '').lower(): continue
            filtered.append(item)
            
        # Sort
        order_list = self.settings.get("CATEGORY_ORDER", [])
        
        def sort_key(x):
            c = x.get('category', 'Other')
            try: c_idx = order_list.index(c)
            except: c_idx = 99
            return (c_idx, int(x.get('order', 9999)))

        filtered.sort(key=sort_key)
        self.filtered_items = filtered
        
        if self.view_mode == "Grouped":
            self._render_grouped_pooled(filtered, order_list)
        else:
            self._render_flat_pooled(filtered)
        
        # Unfreeze scroll frame
        self.scroll_frame.grid()
    
    def _get_or_create_header(self, cat, color, count):
        """Get a header from pool or create new one."""
        if self._header_pool:
            header = self._header_pool.pop()
            # Update existing header
            for child in header.winfo_children():
                child.destroy()
        else:
            header = ctk.CTkFrame(self.scroll_frame, height=30, fg_color="transparent")
        
        ctk.CTkLabel(header, text=f"{cat}", font=ctk.CTkFont(size=14, weight="bold"), 
                   fg_color=color, corner_radius=6, text_color="white").pack(side="left")
        ctk.CTkLabel(header, text=f" ({count}) items", text_color="gray").pack(side="left", padx=5)
        
        header.pack(fill="x", pady=(10, 2))
        self._active_headers.append(header)
        return header
    
    def _get_or_create_row(self, item, flat):
        """Get a row from pool or create new one, then update with item data."""
        if self._row_pool:
            row = self._row_pool.pop()
            # Clear existing content
            for child in row.winfo_children():
                child.destroy()
        else:
            row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        
        self._populate_row(row, item, flat)
        row.pack(fill="x", padx=5, pady=2)
        self._active_rows.append(row)
        self.row_widgets[item['id']] = row
        return row
    
    def _render_grouped_pooled(self, items, order_list):
        groups = {cat: [] for cat in order_list}
        groups['Other'] = []
        
        for item in items:
            c = item.get('category', 'Other')
            if c in groups: groups[c].append(item)
            else: groups['Other'].append(item)
            
        for cat in order_list + ['Other']:
            group_items = groups.get(cat, [])
            if not group_items: continue
            
            color = self.settings.get("CATEGORY_COLORS", {}).get(cat, "gray")
            self._get_or_create_header(cat, color, len(group_items))
            
            for item in group_items:
                self._get_or_create_row(item, flat=False)

    def _render_flat_pooled(self, items):
        for item in items:
            self._get_or_create_row(item, flat=True)
    
    def _populate_row(self, row, item, flat):
        """Populate a row with item data (reused from _create_item_row)."""
        # [Select]
        chk_var = ctk.BooleanVar(value=False)
        self.item_vars[item['id']] = chk_var
        ctk.CTkCheckBox(row, text="", variable=chk_var, width=24).pack(side="left", padx=2)
        
        # Check Dependencies
        if self.package_manager:
            valid, missing = self.package_manager.check_dependencies(item, self.installed_packages)
        else: 
            valid, missing = True, []
        
        # [Enabled Toggle]
        enabled_var = ctk.BooleanVar(value=item.get('enabled', True))
        
        # If missing deps, force disable visual (unless user deliberately wants to toggle it?)
        # Better: keep the var reflecting config, but disable the switch or show warning.
        
        switch = ctk.CTkSwitch(row, text="", width=40, height=20, variable=enabled_var)
        switch.configure(command=lambda: self._on_item_toggle(item, enabled_var, switch))
        switch.pack(side="left", padx=5)
            
        # [Icon]
        icon_img = IconManager.load_icon(item.get('icon', ''))
        if icon_img:
            ctk.CTkLabel(row, text="", image=icon_img, width=30).pack(side="left", padx=2)
        else:
            ctk.CTkLabel(row, text="📄", width=30).pack(side="left", padx=2)
        
        # [Name]
        name_frame = ctk.CTkFrame(row, fg_color="transparent")
        name_frame.pack(side="left", fill="x", expand=True)
        
        if flat:
            cat = item.get('category', 'Custom')
            color = self.settings.get("CATEGORY_COLORS", {}).get(cat, "gray")
            ctk.CTkLabel(name_frame, text="█", text_color=color).pack(side="left", padx=2)
             
        ctk.CTkLabel(name_frame, text=item.get('name', 'Unnamed'), 
                    font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        
        # Warning Label if missing
        if not valid:
             warning_lbl = ctk.CTkLabel(name_frame, text="⚠️", text_color="orange")
             warning_lbl.pack(side="left", padx=2)
             # Tooltip workaround (since ctk has no native tooltip, we use print or status?)
             # Assuming we can't easily add tooltip here without extra lib. 
             # Just basic warning.
        
        # [Hotkey]
        hotkey = item.get('hotkey', '')
        if hotkey:
            ctk.CTkLabel(row, text=hotkey, text_color="orange", width=60).pack(side="left", padx=5)

        # [Order Control]
        order_frame = ctk.CTkFrame(row, fg_color="transparent")
        order_frame.pack(side="left", padx=5)
        ctk.CTkButton(order_frame, text="▲", width=20, height=20, fg_color="transparent", 
                     text_color="gray", hover_color="#333",
                     command=lambda i=item: self.move_item(i, -1)).pack(side="left")
        ctk.CTkButton(order_frame, text="▼", width=20, height=20, fg_color="transparent", 
                     text_color="gray", hover_color="#333",
                     command=lambda i=item: self.move_item(i, 1)).pack(side="left")

        # [Edit]
        ctk.CTkButton(row, text="Edit", width=50, height=24, fg_color=Theme.GRAY_BTN, hover_color=Theme.GRAY_BTN_HOVER,
                     command=lambda i=item: self.open_edit_dialog(i)).pack(side="left", padx=5)
                    
        # [Manual]
        # User requested "doc icon" popup. Replacing "ContextUp" label.
        # using emoji as icon for now, or we could load specific asset.
        ctk.CTkButton(row, text="📄", width=40, height=24, 
                      fg_color=Theme.GRAY_BTN, hover_color=Theme.GRAY_BTN_HOVER,
                      command=lambda i=item: self._open_manual(i)).pack(side="right", padx=5)

    def _open_manual(self, item):
        # Toplevel window shows automatically
        ManualViewerDialog(self.winfo_toplevel(), item)

    def recalculate_orders(self):
        """Force apply the category priority logic to all items.
           Format: (CategoryIndex + 1) * 100 + (ItemIndex + 1)"""
        order_list = self.settings.get("CATEGORY_ORDER", [])
        
        # Group first
        groups = {cat: [] for cat in order_list}
        groups['Other'] = []
        
        # Sort items based on current list order or temporary order to maintain stability
        # But actually, self.filtered_items reflects what the user sees. 
        # If we are just recalculating based on arbitrary 'items', we might lose visual order.
        # Ideally we respect the current sort of 'items' if it's already sorted, or 'filtered_items' if visible.
        # But 'items' is the source of truth.
        
        # Let's rely on self.items being relatively sorted or stable.
        # To be safe, we sort self.items by their *current* order first to ensure stability before re-indexing.
        self.items.sort(key=lambda x: int(x.get('order', 9999)))

        for item in self.items:
            c = item.get('category', 'Other')
            if c in groups: groups[c].append(item)
            else: groups['Other'].append(item)
            
        # Assign IDs
        for cat_idx, cat in enumerate(order_list):
            base_id = (cat_idx + 1) * 100
            for item_idx, item in enumerate(groups[cat]):
                if item['id'] == 'copy_my_info':
                    item['order'] = 9999
                else:
                    # +1 so it starts at .01
                    item['order'] = base_id + (item_idx + 1)
                
        # Handle 'Other' - 9000s
        for idx, item in enumerate(groups['Other']):
            if item['id'] == 'copy_my_info':
                item['order'] = 9999
            else:
                item['order'] = 9000 + (idx + 1)

    def move_item(self, item, direction):
        """Move item up (-1) or down (+1) within its category group using Smart Swap."""
        
        # 1. Find neighbors in *visible* filtered list
        try:
            current_idx = self.filtered_items.index(item)
        except ValueError:
            return # Should not happen

        target_idx = current_idx + direction
        
        # 2. Check bounds
        if not (0 <= target_idx < len(self.filtered_items)):
            return

        neighbor = self.filtered_items[target_idx]
        
        # 3. Restrict to same category
        if item.get('category', 'Other') != neighbor.get('category', 'Other'):
            # Cannot jump categories in this logic
            return

        # 4. Swap Logic
        # A. Update Data Model (filtered list) matches visual
        self.filtered_items[current_idx], self.filtered_items[target_idx] = self.filtered_items[target_idx], self.filtered_items[current_idx]
        
        # B. Update 'order' keys to persist this change
        # We swap the order values so that next full-sort respects this position
        item['order'], neighbor['order'] = neighbor['order'], item['order']

        # C. Update UI (Visual Swap) without rebuild
        w1 = self.row_widgets.get(item['id'])
        w2 = self.row_widgets.get(neighbor['id'])
        
        if w1 and w2:
            if direction > 0: # Down: w1 should be after w2
                w1.pack(after=w2)
            else: # Up: w1 should be before w2
                w1.pack(before=w2)
        
        # D. Skip full refresh!
        # Status update? Maybe subtle.
        pass


    def auto_organize(self):
        self.recalculate_orders()
        self.refresh_list()
        tkinter.messagebox.showinfo("Organize", "Items re-ordered (Hundreds for Category, Units for Items).")
        
    def open_add_dialog(self):
        ItemEditorDialog(self.winfo_toplevel(), on_save=self.add_item)

    def open_edit_dialog(self, item):
        ItemEditorDialog(self.winfo_toplevel(), item_data=item, 
                        on_save=lambda new_data: self.update_item(item, new_data), 
                        on_delete=lambda: self.delete_item(item))

    def add_item(self, new_item):
        self.items.append(new_item)
        self.recalculate_orders() # Auto calc on add
        self.refresh_list()

    def update_item(self, old_item, new_data):
        for k, v in new_data.items(): old_item[k] = v
        self.recalculate_orders() # Category might have changed
        self.refresh_list()
        
    def delete_item(self, item):
        if item in self.items: self.items.remove(item)
        self.refresh_list()

    def save_final(self):
        # Ensure order is fresh
        self.recalculate_orders()
        
        # save_config now returns (success, message) tuple
        result = self.config_manager.save_config(self.items, self.settings)
        
        if isinstance(result, tuple):
            success, message = result
        else:
            # Backward compatibility
            success, message = result, "Configuration saved."
        
        if success:
            # Trigger Registry Update if available
            if self.on_save_registry:
                # self.on_save_registry() # Global Apply handles this now
                pass 
            else:
                pass # Global Apply handles this now
                # tkinter.messagebox.showinfo("Success", message) 
        else:
            tkinter.messagebox.showerror("Error", message)

    def save(self):
        """Standard interface for Global Apply."""
        # Use save_final but suppress success message since Global Apply shows one.
        # But save_final logic above: if on_save_registry is None (which it is provided by app.py lambda), 
        # it might trigger something.
        # Actually app.py passes `on_save_registry=self.apply_registry_changes`.
        # When we click Global Save, app.py calls `editor.save()`, then `save_settings()`, then `apply_registry_changes()`.
        # So we don't need `editor.save()` to call `on_save_registry` again.
        
        # We need to save the CONFIG to disk.
        self.recalculate_orders()
        result = self.config_manager.save_config(self.items, self.settings)
        # Note: We rely on global apply to show success/failure summaries, 
        # but if save_config fails, we should probably throw or log.
        if isinstance(result, tuple):
            success, msg = result
            if not success: 
                raise Exception(msg)
        elif not result:
             raise Exception("Unknown save error")


