import os
import re
import sys
import shutil
import threading
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN
from utils.batch_runner import collect_batch_context
from utils.files import get_safe_path
from core.logger import setup_logger

logger = setup_logger("sequence_analyze")

class SequenceAnalyzer:
    """Core logic for detecting and analyzing sequences."""
    VALID_EXTS = {'.jpg', '.jpeg', '.png', '.exr', '.tga', '.tif', '.tiff', '.bmp', '.webp', '.hdr', '.dpx'}

    def __init__(self):
        self.pattern = re.compile(r"^(.*?)(\d+)(\.[a-zA-Z0-9]+)$")

    def find_sequences(self, files):
        sequences = {}
        for f in files:
            if f.name.startswith('.'): continue
            
            match = self.pattern.match(f.name)
            if match:
                prefix, num_str, ext = match.groups()
                if ext.lower() not in self.VALID_EXTS: continue
                
                key = (prefix, ext, f.parent)
                if key not in sequences:
                    sequences[key] = {
                        'prefix': prefix,
                        'ext': ext,
                        'parent': f.parent,
                        'frames': [],
                        'files': []
                    }
                sequences[key]['frames'].append(int(num_str))
                sequences[key]['files'].append(f)
        
        results = []
        for key, data in sequences.items():
            data['frames'].sort()
            data['files'].sort(key=lambda x: x.name)
            
            # Missing frames
            missing = []
            if len(data['frames']) > 1:
                full_range = set(range(data['frames'][0], data['frames'][-1] + 1))
                existing = set(data['frames'])
                missing = sorted(list(full_range - existing))
            data['missing'] = missing
            
            # IMPROVED: Sample resolution from first 3 valid frames
            data['corrupted'] = []
            data['collisions'] = []
            data['errors'] = []  # NEW: Track error types
            data['resolution'] = None
            
            for sample_file in data['files'][:3]:
                try:
                    if sample_file.stat().st_size > 0:
                        with Image.open(sample_file) as img:
                            data['resolution'] = img.size
                            break
                except:
                    continue
            
            results.append(data)
            
        return results

    def verify_sequence_integrity(self, sequence_data, cancel_event=None, callback=None):
        """Deep check with cancel support and detailed error types."""
        corrupted = []
        collisions = []
        errors = []
        first_res = sequence_data.get('resolution')
        files = sequence_data['files']
        
        def check_file(f):
            try:
                if f.stat().st_size == 0:
                    return f, "corrupted", "Empty file"
                with Image.open(f) as img:
                    res = img.size
                    img.verify()
                    if first_res and res != first_res:
                        return f, "collision", res
            except PermissionError:
                return f, "error", "Permission denied"
            except OSError as e:
                if "Network" in str(e) or "I/O" in str(e):
                    return f, "error", f"IO Error: {e}"
                return f, "corrupted", str(e)
            except Exception as e:
                return f, "corrupted", str(e)
            return f, "ok", None

        max_workers = min(os.cpu_count() or 4, 8)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_file, f): f for f in files}
            
            for i, future in enumerate(as_completed(futures)):
                if cancel_event and cancel_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    return corrupted, collisions, errors
                
                f, status, detail = future.result()
                if status == "corrupted":
                    corrupted.append(f)
                    logger.debug(f"Corrupted: {f.name} - {detail}")
                elif status == "collision":
                    collisions.append((f, detail))
                elif status == "error":
                    errors.append((f, detail))
                    logger.warning(f"Error: {f.name} - {detail}")
                
                if callback:
                    callback(i + 1, len(files))

        return corrupted, collisions, errors


class SequenceAnalyzeGUI(BaseWindow):
    def __init__(self, target_paths):
        super().__init__(title="Sequence Analyze", width=900, height=650, icon_name="sequence_analyze")
        self.analyzer = SequenceAnalyzer()
        self.all_sequences = []
        self.recursive_var = tk.BooleanVar(value=False)
        self.deep_check_cancel = threading.Event()
        self.deep_check_running = False
        
        if isinstance(target_paths, (list, tuple)):
            self.targets = [Path(p) for p in target_paths]
        else:
            self.targets = [Path(target_paths)]
            
        self.create_widgets()
        self.start_analysis()

    def create_widgets(self):
        # Footer
        footer = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=20, pady=10)
        
        self.btn_arrange = ctk.CTkButton(footer, text="Arrange into Folders", command=self.run_arrange, state="disabled")
        self.btn_arrange.pack(side="left", padx=5)
        
        self.btn_clean = ctk.CTkButton(footer, text="Move Corrupted", fg_color="#E74C3C", hover_color="#C0392B", command=self.run_clean, state="disabled")
        self.btn_clean.pack(side="left", padx=5)
        
        self.btn_report = ctk.CTkButton(footer, text="Export Report", fg_color="transparent", border_width=1, command=self.export_report, state="disabled")
        self.btn_report.pack(side="right", padx=5)

        # Header
        self.add_header("Sequence Analysis & Integrity Check")
        
        # Toolbar
        toolbar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        toolbar.pack(side="top", fill="x", padx=20, pady=(0, 5))
        
        self.cb_recursive = ctk.CTkCheckBox(toolbar, text="Recursive", variable=self.recursive_var, command=self.start_analysis)
        self.cb_recursive.pack(side="left", padx=5)
        
        self.btn_deep_all = ctk.CTkButton(toolbar, text="Deep Check All", width=100, command=self.run_deep_check_all)
        self.btn_deep_all.pack(side="left", padx=10)
        
        self.btn_cancel = ctk.CTkButton(toolbar, text="Cancel", width=70, fg_color="#E74C3C", command=self.cancel_deep_check)
        self.btn_cancel.pack(side="left", padx=5)
        self.btn_cancel.pack_forget()  # Hidden by default
        
        self.btn_refresh = ctk.CTkButton(toolbar, text="Refresh", width=80, fg_color="transparent", border_width=1, command=self.start_analysis)
        self.btn_refresh.pack(side="right", padx=5)
        
        # Status & Progress
        status_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        status_frame.pack(side="top", fill="x", padx=20, pady=2)
        
        self.lbl_status = ctk.CTkLabel(status_frame, text="Ready", text_color="gray", font=ctk.CTkFont(size=11))
        self.lbl_status.pack(side="left")
        
        self.progress = ctk.CTkProgressBar(status_frame, width=200, height=10)
        self.progress.pack(side="right", padx=10)
        self.progress.set(0)
        self.progress.pack_forget()  # Hidden by default
        
        # Treeview Table
        tree_frame = ctk.CTkFrame(self.main_frame)
        tree_frame.pack(side="top", fill="both", expand=True, padx=20, pady=5)
        
        # Style for dark theme
        # Style for dark theme (Unified)
        style = ttk.Style()
        style.theme_use("clam")
        
        # Theme constants applied directly
        tree_bg = THEME_CARD
        tree_fg = "#E0E0E0"
        field_bg = THEME_CARD
        head_bg = THEME_DROPDOWN_FG
        head_fg = "#E0E0E0"
        head_active = THEME_DROPDOWN_BTN
        selected_bg = THEME_BTN_PRIMARY

        style.configure("Treeview", 
                       background=tree_bg, 
                       foreground=tree_fg, 
                       fieldbackground=field_bg,
                       bordercolor=tree_bg,
                       lightcolor=tree_bg,
                       darkcolor=tree_bg,
                       rowheight=24,
                       font=("Segoe UI", 10))
        style.configure("Treeview.Heading", 
                       background=head_bg, 
                       foreground=head_fg,
                       bordercolor=THEME_BORDER,
                       font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", selected_bg)])
        style.map("Treeview.Heading", background=[("active", head_active)])

        
        columns = ("name", "frames", "missing", "issues", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        
        self.tree.heading("name", text="Sequence Name", anchor="w")
        self.tree.heading("frames", text="Frames / Resolution", anchor="w")
        self.tree.heading("missing", text="Miss", anchor="center")
        self.tree.heading("issues", text="Issues", anchor="w")
        self.tree.heading("status", text="Status", anchor="center")
        
        self.tree.column("name", width=350, minwidth=200)
        self.tree.column("frames", width=180, minwidth=120)
        self.tree.column("missing", width=60, minwidth=50, anchor="center")
        self.tree.column("issues", width=120, minwidth=80)
        self.tree.column("status", width=80, minwidth=60, anchor="center")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Context menu
        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Deep Check Selected", command=lambda: self.run_deep_check_selected([item]))
            menu.add_command(label="Open Folder", command=lambda: self.open_sequence_folder(item))
            menu.tk_popup(event.x_root, event.y_root)

    def open_sequence_folder(self, item_id):
        idx = int(item_id.replace("seq_", ""))
        if 0 <= idx < len(self.all_sequences):
            os.startfile(self.all_sequences[idx]['parent'])

    def start_analysis(self):
        threading.Thread(target=self.run_analysis, daemon=True).start()

    def run_analysis(self):
        try:
            self.after(0, lambda: self.lbl_status.configure(text="Scanning..."))
            all_files = []
            is_recursive = self.recursive_var.get()
            
            for t in self.targets:
                if t.is_dir():
                    if is_recursive:
                        for root, dirs, files in os.walk(t):
                            for f in files:
                                all_files.append(Path(root) / f)
                    else:
                        all_files.extend([f for f in t.iterdir() if f.is_file()])
                else:
                    all_files.append(t)
            
            if not all_files:
                self.after(0, lambda: self.lbl_status.configure(text="No files found."))
                return

            self.all_sequences = self.analyzer.find_sequences(all_files)
            self.after(0, self.update_ui)
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def update_ui(self):
        self.tree.delete(*self.tree.get_children())
        
        if not self.all_sequences:
            self.lbl_status.configure(text="No sequences found.")
            return

        for i, seq in enumerate(self.all_sequences):
            res_str = f" [{seq['resolution'][0]}x{seq['resolution'][1]}]" if seq['resolution'] else ""
            frames_text = f"{seq['frames'][0]}-{seq['frames'][-1]} ({len(seq['frames'])}){res_str}"
            m_count = len(seq['missing'])
            
            self.tree.insert("", "end", iid=f"seq_{i}", values=(
                f"{seq['prefix']}*{seq['ext']}",
                frames_text,
                str(m_count) if m_count > 0 else "-",
                "-",
                "Ready"
            ))

        self.lbl_status.configure(text=f"Found {len(self.all_sequences)} sequences.")
        self.btn_arrange.configure(state="normal")
        self.btn_report.configure(state="normal")

    def run_deep_check_all(self):
        items = self.tree.get_children()
        if items:
            self.run_deep_check_selected(list(items))

    def run_deep_check_selected(self, items):
        if self.deep_check_running:
            return
            
        self.deep_check_running = True
        self.deep_check_cancel.clear()
        self.btn_cancel.pack(side="left", padx=5)
        self.progress.pack(side="right", padx=10)
        self.progress.set(0)
        self.btn_deep_all.configure(state="disabled")
        
        threading.Thread(target=lambda: self._deep_check_worker(items), daemon=True).start()

    def _deep_check_worker(self, items):
        total_items = len(items)
        
        for idx, item_id in enumerate(items):
            if self.deep_check_cancel.is_set():
                break
                
            seq_idx = int(item_id.replace("seq_", ""))
            seq = self.all_sequences[seq_idx]
            
            self.after(0, lambda i=item_id: self.tree.set(i, "status", "Checking..."))
            
            def progress_callback(curr, total):
                pct = (idx + curr/total) / total_items
                self.after(0, lambda p=pct: self.progress.set(p))
            
            corr, coll, errs = self.analyzer.verify_sequence_integrity(
                seq, cancel_event=self.deep_check_cancel, callback=progress_callback
            )
            
            seq['corrupted'] = corr
            seq['collisions'] = coll
            seq['errors'] = errs
            
            # Update UI
            c_count = len(corr)
            col_count = len(coll)
            err_count = len(errs)
            
            parts = []
            if c_count > 0: parts.append(f"{c_count} Corr")
            if col_count > 0: parts.append(f"{col_count} Split")
            if err_count > 0: parts.append(f"{err_count} Err")
            issues_text = " / ".join(parts) if parts else "-"
            
            status = "Verified" if not self.deep_check_cancel.is_set() else "Cancelled"
            self.after(0, lambda i=item_id, t=issues_text, s=status: (
                self.tree.set(i, "issues", t),
                self.tree.set(i, "status", s)
            ))
        
        self.after(0, self._finish_deep_check_all)

    def _finish_deep_check_all(self):
        self.deep_check_running = False
        self.btn_cancel.pack_forget()
        self.progress.pack_forget()
        self.btn_deep_all.configure(state="normal")
        
        total_corrupted = sum(len(s['corrupted']) for s in self.all_sequences)
        if total_corrupted > 0:
            self.btn_clean.configure(state="normal", text=f"Move {total_corrupted} Corrupted")
        
        if self.deep_check_cancel.is_set():
            self.lbl_status.configure(text="Deep check cancelled.")
        else:
            self.lbl_status.configure(text="Deep check complete.")

    def cancel_deep_check(self):
        self.deep_check_cancel.set()
        self.lbl_status.configure(text="Cancelling...")

    def run_arrange(self):
        if not messagebox.askyesno("Confirm", "Move files into folders based on sequence names?"):
            return
            
        count = 0
        for seq in self.all_sequences:
            dest = seq['parent'] / seq['prefix'].strip(" _-.")
            dest.mkdir(exist_ok=True)
            for f in seq['files']:
                try:
                    shutil.move(str(f), str(dest / f.name))
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to move {f.name}: {e}")
        
        messagebox.showinfo("Success", f"Moved {count} files.")
        self.start_analysis()

    def run_clean(self):
        corrupted_files = []
        for seq in self.all_sequences:
            corrupted_files.extend(seq['corrupted'])
            
        if not corrupted_files: return
        
        if not messagebox.askyesno("Confirm", f"Move {len(corrupted_files)} corrupted files?"):
            return
            
        dest_root = self.targets[0] if self.targets[0].is_dir() else self.targets[0].parent
        corrupted_dir = dest_root / "_corrupted"
        corrupted_dir.mkdir(exist_ok=True)
        
        count = 0
        for f in corrupted_files:
            try:
                shutil.move(str(f), str(corrupted_dir / f.name))
                count += 1
            except Exception as e:
                logger.error(f"Failed to move {f.name}: {e}")
        
        messagebox.showinfo("Success", f"Moved {count} files.")
        self.start_analysis()

    def export_report(self):
        report_lines = [f"Sequence Analysis Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
        report_lines.append("-" * 50)
        
        for seq in self.all_sequences:
            report_lines.append(f"Sequence: {seq['prefix']}*{seq['ext']}")
            report_lines.append(f"  Range: {seq['frames'][0]} - {seq['frames'][-1]}")
            report_lines.append(f"  Total Frames: {len(seq['frames'])}")
            if seq['missing']:
                from utils.system_tools import format_missing_ranges
                report_lines.append(f"  Missing ({len(seq['missing'])}): {format_missing_ranges(seq['missing'])}")
            if seq['corrupted']:
                report_lines.append(f"  Corrupted: {len(seq['corrupted'])}")
            if seq.get('errors'):
                report_lines.append(f"  Errors: {len(seq['errors'])}")
            report_lines.append("")
            
        save_dir = self.targets[0] if self.targets[0].is_dir() else self.targets[0].parent
        out_path = get_safe_path(save_dir / f"SequenceReport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
            
        os.startfile(out_path)

if __name__ == "__main__":
    if "--test" in sys.argv:
        test_path = Path(sys.argv[sys.argv.index("--test") + 1])
        print(f"Testing: {test_path}")
        analyzer = SequenceAnalyzer()
        all_files = []
        if test_path.is_dir():
            for root, dirs, files in os.walk(test_path):
                for f in files:
                    all_files.append(Path(root) / f)
        
        results = analyzer.find_sequences(all_files)
        for seq in results:
            print(f"\n{seq['prefix']}*{seq['ext']}: {len(seq['frames'])} frames")
            if seq['missing']: print(f"  MISSING: {len(seq['missing'])}")
        sys.exit(0)

    if "--demo" in sys.argv or "--test-screenshot" in sys.argv:
        app = SequenceAnalyzeGUI([])
        app.mainloop()
        sys.exit(0)

    if len(sys.argv) > 1:
        anchor = sys.argv[1]
        paths = collect_batch_context("sequence_analyze", anchor)
        
        if paths:
            app = SequenceAnalyzeGUI(paths)
            app.mainloop()
        else:
            logger.debug(f"Follower exiting for {anchor}")
            sys.exit(0)
    else:
        # Default empty launch if no args
        app = SequenceAnalyzeGUI([])
        app.mainloop()

