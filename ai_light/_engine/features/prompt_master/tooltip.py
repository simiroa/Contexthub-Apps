import customtkinter as ctk

class Tooltip:
    def __init__(self, widget, text, delay=300):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<ButtonPress>", self.hide_tooltip)

    def schedule_tooltip(self, event=None):
        self.id = self.widget.after(self.delay, self.show_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Make it transparent-ish or just a nice box
        # Windows specific transparency
        # self.tooltip_window.attributes("-transparentcolor", "white") 
        
        label = ctk.CTkLabel(
            self.tooltip_window, 
            text=self.text, 
            fg_color="gray20", 
            text_color="gray90",
            corner_radius=6,
            font=ctk.CTkFont(size=12),
            padx=8,
            pady=4
        )
        label.pack()
        
        # Ensure it's on top
        self.tooltip_window.attributes("-topmost", True)

    def hide_tooltip(self, event=None):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
