import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import queue
import time
from pathlib import Path
import sys

# Add src to path to import gui_lib
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.append(str(src_dir))

from .gui_lib import setup_theme

class BatchProgressGUI(ctk.CTkToplevel):
    def __init__(self, title, items, process_func, on_complete=None):
        """
        Generic Batch Progress Window (Modernized).
        """
        super().__init__()
        setup_theme()
        
        self.title(title)
        self.geometry("600x350")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        self.items = items
        self.process_func = process_func
        self.on_complete = on_complete
        
        self.is_cancelled = False
        self.is_running = False
        self.queue = queue.Queue()
        
        self.success_count = 0
        self.errors = []
        
        self._create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        # Center window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # Start processing automatically
        self.start_processing()
        
    def _create_widgets(self):
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Status Label
        self.lbl_status = ctk.CTkLabel(main_frame, text="Ready...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status.pack(anchor="w", padx=20, pady=(20, 5))
        
        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(main_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=(5, 5))
        self.progress_bar.set(0)
        
        # Counter Label
        self.lbl_counter = ctk.CTkLabel(main_frame, text=f"0 / {len(self.items)}", text_color="gray")
        self.lbl_counter.pack(anchor="e", padx=20, pady=(0, 10))
        
        # Log Area
        self.log_text = ctk.CTkTextbox(main_frame, height=100, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Buttons
        self.btn_cancel = ctk.CTkButton(main_frame, text="Stop", fg_color="#C0392B", hover_color="#E74C3C", command=self.on_cancel)
        self.btn_cancel.pack(side="right", padx=20, pady=(0, 20))
        
    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        
    def start_processing(self):
        self.is_running = True
        self.btn_cancel.configure(text="Stop")
        self.lbl_status.configure(text="Processing...")
        
        # Start thread
        threading.Thread(target=self._worker, daemon=True).start()
        
        # Start polling queue
        self.after(100, self._poll_queue)
        
    def _worker(self):
        for i, item in enumerate(self.items):
            if self.is_cancelled:
                break
                
            # Update UI: Start of item
            self.queue.put(("start_item", (i, item)))
            
            try:
                # Run processing
                def update_msg(msg):
                    self.queue.put(("msg", msg))
                    
                success, error_msg = self.process_func(item, update_msg)
                
                self.queue.put(("end_item", (success, error_msg)))
                
            except Exception as e:
                self.queue.put(("end_item", (False, str(e))))
                
        self.queue.put(("done", None))
        
    def _poll_queue(self):
        try:
            while True:
                msg_type, data = self.queue.get_nowait()
                
                if msg_type == "start_item":
                    idx, item = data
                    name = str(item)
                    if hasattr(item, 'name'): name = item.name
                    self.lbl_status.configure(text=f"Processing: {name}")
                    self.progress_bar.set(idx / len(self.items))
                    
                elif msg_type == "msg":
                    self.lbl_status.configure(text=data)
                    
                elif msg_type == "end_item":
                    success, error_msg = data
                    current_val = self.progress_bar.get()
                    # Approximate progress update (exact calculation is tricky with float)
                    # Just rely on start_item for main progress, or update here
                    
                    self.lbl_counter.configure(text=f"{self.success_count + (1 if success else 0) + len(self.errors)} / {len(self.items)}")
                    
                    if success:
                        self.success_count += 1
                    else:
                        self.errors.append(error_msg)
                        self.log(f"Error: {error_msg}")
                        
                elif msg_type == "done":
                    self.is_running = False
                    self._finish()
                    return
                    
        except queue.Empty:
            pass
            
        if self.is_running:
            self.after(100, self._poll_queue)
            
    def on_cancel(self):
        if self.is_running:
            if messagebox.askyesno("Stop", "Are you sure you want to stop the process?"):
                self.is_cancelled = True
                self.lbl_status.configure(text="Stopping...")
                self.btn_cancel.configure(state="disabled")
        else:
            self.destroy()
            
    def _finish(self):
        self.progress_bar.set(1.0)
        self.btn_cancel.configure(text="Close", state="normal", fg_color="gray", hover_color="gray", command=self.destroy)
        
        if self.is_cancelled:
            self.lbl_status.configure(text="Stopped by user.", text_color="orange")
            self.log("Process stopped by user.")
        else:
            self.lbl_status.configure(text="Completed.", text_color="green")
            self.log("Process completed.")
            
        # Show summary
        if self.errors:
            messagebox.showwarning("Completed with Errors", 
                f"Processed: {self.success_count}/{len(self.items)}\n"
                f"Errors: {len(self.errors)}\n\n"
                "Check the log for details.")
        else:
            if not self.is_cancelled:
                messagebox.showinfo("Success", f"Successfully processed {self.success_count} items.")
            
        if self.on_complete:
            self.on_complete(self.success_count, self.errors)

def run_batch_gui(title, items, process_func, parent=None):
    """Helper to run the GUI."""
    if not items: return
    
    # We don't need a hidden root with CTk usually, but good to have app context
    # If parent is provided, use it?
    # For standalone scripts, we create a dummy app if needed, but CTkToplevel needs a root CTk
    
    # Check if we have a running CTk app
    # If not, we might need to create one.
    # But run_batch_gui is often called from scripts that just have 'tk.Tk()' hidden.
    
    # Strategy: Create a hidden CTk root if none exists
    root = None
    try:
        if ctk.CTk._root_window is None:
             root = ctk.CTk()
             root.withdraw()
    except:
        pass

    app = BatchProgressGUI(title, items, process_func)
    app.mainloop()

