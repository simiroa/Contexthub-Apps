import tkinter.messagebox
import customtkinter as ctk
from manager.ui.theme import Theme
import os
import locale
from PIL import Image

class ManualViewerDialog(ctk.CTkToplevel):
    """
    Multi-language manual viewer.
    
    Folder structure:
        docs/manuals/ko/       <- Korean (or default)
        docs/manuals/en/       <- English
        docs/manuals/images/   <- Shared images (language-independent)
        
    Fallback chain: locale_folder -> default folder
    """
    
    def __init__(self, parent, item_data, manuals_dir="docs/manuals", lang=None):
        super().__init__(parent)
        
        self.item_data = item_data
        self.manuals_dir = manuals_dir
        
        # Auto-detect language from system locale if not specified
        # Supported: 'ko', 'en' (more can be added)
        if lang is None:
            system_lang, _ = locale.getlocale()
            if system_lang and system_lang.lower().startswith('ko'):
                self.lang = 'ko'
            else:
                self.lang = 'ko'  # Default to Korean for now
        else:
            self.lang = lang
        
        self.title(f"Manual: {item_data.get('name', 'Unknown')}")
        self.geometry("600x700")
        
        # Bring to front and focus
        self.lift()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))
        self.focus_force()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 1. Header (Window Title Bar area - minimal)
        self.header_frame = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew")
        
        # 2. Main Scrollable Content
        self.scroll_frame = ctk.CTkScrollableFrame(self, bg_color="transparent", fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # 3. Footer
        self.footer = ctk.CTkFrame(self, height=50, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkButton(self.footer, text="Edit File", command=self.open_file_external, width=100,
                     fg_color=Theme.GRAY_BTN, hover_color=Theme.GRAY_BTN_HOVER).pack(side="left")
        
        ctk.CTkButton(self.footer, text="Close", command=self.destroy, width=100,
                      fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER).pack(side="right")
                      
        self.load_content()

    def _get_localized_path(self, base_dir, filename):
        """
        Get localized file path with fallback.
        Priority: lang folder -> root folder
        """
        lang_path = os.path.join(base_dir, self.lang, filename)
        if os.path.exists(lang_path):
            return lang_path
        
        # Fallback to root manuals folder
        root_path = os.path.join(base_dir, filename)
        return root_path
        
    def load_content(self):
        # Resolve Paths
        item_id = self.item_data.get('id', '')
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
        full_manuals_dir = os.path.join(root_dir, self.manuals_dir)
        full_images_dir = os.path.join(full_manuals_dir, "images")
        
        # 1. Render Image (Top) - Images are shared across languages
        img_path = os.path.join(full_images_dir, f"{item_id}.png")
        if not os.path.exists(img_path):
             img_path = os.path.join(full_images_dir, f"{item_id}.jpg")
        if not os.path.exists(img_path):
             img_path = os.path.join(full_images_dir, f"{item_id}.gif")
        
        self._render_image(img_path)
        
        # 2. Render Text Content - Localized with fallback
        md_path = self._get_localized_path(full_manuals_dir, f"{item_id}.md")
        self.current_file = md_path
        
        if os.path.exists(md_path):
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self._render_markdown(content)
            except Exception as e:
                self._render_text(f"Error loading manual: {e}", color="red")
        else:
            # Show placeholder
            self._render_header(self.item_data.get('name', 'Unknown Title'), level=1)
            self._render_text("No manual found. Click 'Edit File' to create one.")
            self._render_section_break()
            self._render_header("Introduction", level=2)
            self._render_text("Add a brief description of the tool here.")
            self._render_header("Usage", level=2)
            self._render_text("1. Step one\n2. Step two")


    def _render_image(self, img_path):
        """Render the banner image or a placeholder. Supports GIF animations."""
        container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        container.pack(fill="x", pady=(0, 20))
        
        if os.path.exists(img_path):
            try:
                pil_img = Image.open(img_path)
                
                # Check if it's an animated GIF
                is_animated = getattr(pil_img, "is_animated", False)
                
                if is_animated:
                    self._animate_gif(container, img_path)
                else:
                    self._show_static_image(container, pil_img)
                    
            except Exception as e:
                ctk.CTkLabel(container, text=f"Image Error: {e}").pack()
        else:
            # Placeholder
            placeholder = ctk.CTkFrame(container, height=200, fg_color=Theme.BG_HOVER)
            placeholder.pack(fill="x")
            ctk.CTkLabel(placeholder, text="[Screenshot Area]\nAdd image to docs/manuals/images/{id}.png", 
                        text_color="gray").place(relx=0.5, rely=0.5, anchor="center")

    def _show_static_image(self, container, pil_img):
        w, h = pil_img.size
        target_w = 540
        target_h = int(h * (target_w / w))
        if target_h > 300: target_h = 300
        
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))
        lbl = ctk.CTkLabel(container, text="", image=ctk_img)
        lbl.pack(anchor="center")

    def _animate_gif(self, container, img_path):
        """Simple GIF animation loop."""
        pil_gif = Image.open(img_path)
        frames = []
        try:
            while True:
                # Resize each frame
                w, h = pil_gif.size
                target_w = 540
                target_h = int(h * (target_w / w))
                if target_h > 300: target_h = 300
                
                frame = pil_gif.copy().convert("RGBA").resize((target_w, target_h), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=frame, dark_image=frame, size=(target_w, target_h))
                
                duration = pil_gif.info.get("duration", 100)
                frames.append((ctk_img, duration))
                pil_gif.seek(pil_gif.tell() + 1)
        except EOFError:
            pass

        if not frames: return

        lbl = ctk.CTkLabel(container, text="")
        lbl.pack(anchor="center")

        def update(idx):
            if not lbl.winfo_exists(): return
            img, delay = frames[idx]
            lbl.configure(image=img)
            next_idx = (idx + 1) % len(frames)
            self.after(delay, update, next_idx)

        update(0)

    def _render_markdown(self, text):
        """Simple line-by-line markdown parser."""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('# '):
                self._render_header(line[2:], level=1)
            elif line.startswith('## '):
                self._render_header(line[3:], level=2)
            elif line.startswith('### '):
                self._render_header(line[4:], level=3)
            elif line.startswith('- ') or line.startswith('* '):
                self._render_bullet(line[2:])
            elif line[0].isdigit() and line[1:3] == '. ':
                 self._render_bullet(line, is_numbered=True)
            else:
                self._render_text(line)

    def _render_header(self, text, level=1):
        if level == 1:
            font = ctk.CTkFont(size=26, weight="bold")
            color = Theme.TEXT_MAIN
            pady = (20, 10)
        elif level == 2:
            font = ctk.CTkFont(size=20, weight="bold")
            color = Theme.ACCENT  # Use accent color for H2
            pady = (15, 5)
        else:
            font = ctk.CTkFont(size=16, weight="bold")
            color = Theme.TEXT_MAIN
            pady = (10, 5)
            
        label = ctk.CTkLabel(self.scroll_frame, text=text, font=font, text_color=color, anchor="w", justify="left")
        label.pack(fill="x", padx=10, pady=pady)
        
        # Add separator for H1/H2
        if level <= 2:
             sep = ctk.CTkFrame(self.scroll_frame, height=2, fg_color=Theme.BORDER)
             sep.pack(fill="x", padx=10, pady=(0, 10))

    def _render_text(self, text, color=None):
        if color is None: color = "gray90"
        label = ctk.CTkLabel(self.scroll_frame, text=text, font=ctk.CTkFont(size=14), 
                           text_color=color, anchor="w", justify="left", wraplength=550)
        label.pack(fill="x", padx=20, pady=2)

    def _render_bullet(self, text, is_numbered=False):
        frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=2)
        
        bullet_char = "•" if not is_numbered else "" 
        # If numbered, the text usually includes the number "1. "
        
        if not is_numbered:
            ctk.CTkLabel(frame, text=bullet_char, width=20, anchor="n", font=ctk.CTkFont(size=18)).pack(side="left", anchor="n")
            
        ctk.CTkLabel(frame, text=text, font=ctk.CTkFont(size=14), 
                   text_color="gray90", anchor="w", justify="left", wraplength=510).pack(side="left", fill="x", expand=True)

    def _render_section_break(self):
        ctk.CTkFrame(self.scroll_frame, height=20, fg_color="transparent").pack()

    def open_file_external(self):
        if self.current_file:
            # If it doesn't exist, create it empty so user can edit
            if not os.path.exists(self.current_file):
                try:
                    with open(self.current_file, "w", encoding="utf-8") as f:
                        f.write(f"# {self.item_data.get('name')}\n\n## Introduction\nBrief description.\n\n## Usage\n1. Step one")
                except Exception as e:
                    tkinter.messagebox.showerror("Error", f"Could not create file: {e}")
                    return
            
            os.startfile(self.current_file)
