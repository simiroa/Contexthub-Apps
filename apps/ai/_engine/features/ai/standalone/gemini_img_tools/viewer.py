"""
Gemini Image Tools - Image Viewer Component
Zoomable and pannable image viewer widget.
"""
import cv2
import customtkinter as ctk
from tkinter import Canvas
from PIL import Image, ImageTk


class ImageViewer(ctk.CTkFrame):
    """Zoomable and pannable image viewer widget."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.canvas = Canvas(self, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.image = None
        self.tk_image = None
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.start_x = 0
        self.start_y = 0
        
        # Bind events
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", self.on_zoom)  # Linux scroll
        self.canvas.bind("<Button-5>", self.on_zoom)  # Linux scroll
        self.canvas.bind("<Configure>", self.on_resize)

    def on_resize(self, event):
        """Handle window resize."""
        if self.image:
            self.redraw()

    def load_image(self, cv_img):
        """Load a CV2 image into the viewer."""
        self.image = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
        self.reset_view()
        self.redraw()

    def reset_view(self):
        """Reset zoom and pan to fit the image in the window."""
        if not self.image:
            return
        # Fit to window
        cw = self.canvas.winfo_width() or 500
        ch = self.canvas.winfo_height() or 500
        iw, ih = self.image.size
        self.scale = min(cw / iw, ch / ih) * 0.9
        self.pan_x = cw // 2
        self.pan_y = ch // 2
        self.redraw()

    def redraw(self):
        """Redraw the image on the canvas."""
        if not self.image:
            return
        
        w, h = self.image.size
        new_w = int(w * self.scale)
        new_h = int(h * self.scale)
        
        if new_w <= 0 or new_h <= 0:
            return
        
        resized = self.image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        
        self.canvas.delete("all")
        self.canvas.create_image(self.pan_x, self.pan_y, image=self.tk_image, anchor="center")

    def on_drag_start(self, event):
        """Start dragging."""
        self.start_x = event.x
        self.start_y = event.y

    def on_drag_motion(self, event):
        """Handle drag motion."""
        dx = event.x - self.start_x
        dy = event.y - self.start_y
        self.pan_x += dx
        self.pan_y += dy
        self.start_x = event.x
        self.start_y = event.y
        self.redraw()

    def on_zoom(self, event):
        """Handle zoom via mouse wheel."""
        if event.num == 5 or event.delta < 0:
            self.scale *= 0.9
        else:
            self.scale *= 1.1
        self.redraw()
