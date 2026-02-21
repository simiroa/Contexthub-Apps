import os
import json
import customtkinter as ctk
from PIL import Image
from ..constants import PRESETS_DIR
from ..tooltip import Tooltip

class ImageMixin:
    def add_corners(self, im, rad):
        """Add rounded corners to an image"""
        from PIL import Image, ImageDraw
        
        circle = Image.new('L', (rad * 2, rad * 2), 0)
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, rad * 2, rad * 2), fill=255)
        
        alpha = Image.new('L', im.size, 255)
        w, h = im.size
        
        alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
        alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
        alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
        alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
        
        im.putalpha(alpha)
        return im

    def paste_image_from_clipboard(self):
        """Paste image from clipboard and display it"""
        from PIL import ImageGrab, Image
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                self.current_raw_image = img.copy() # Store raw for saving
                
                # Resize and display
                target_w = 250
                ratio = target_w / img.width
                target_h = int(img.height * ratio)
                
                # Resize
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                self.current_displayed_image = img # Store resized
                
                # Add corners
                img = self.add_corners(img, 15)
                
                img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(target_w, target_h))
                
                # Clear previous
                for widget in self.image_panel.winfo_children():
                    widget.destroy()
                    
                img_label = ctk.CTkLabel(self.image_panel, image=img_ctk, text="")
                img_label.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
                
                # Add paste button overlay (small icon)
                self.add_image_overlay_buttons()
            else:
                print("No image in clipboard")
        except Exception as e:
            print(f"Paste error: {e}")

    def add_image_overlay_buttons(self):
        """Add floating paste and save buttons on the image panel"""
        # Paste Button
        paste_btn = ctk.CTkButton(
            self.image_panel,
            text="📋",
            width=30,
            height=30,
            fg_color="gray20",
            hover_color="gray30",
            command=self.paste_image_from_clipboard,
            border_spacing=0
        )
        paste_btn.place(relx=0.95, rely=0.95, anchor="se")
        Tooltip(paste_btn, "Paste from Clipboard")
        
        # Save Button (only if we have a current image)
        if hasattr(self, 'current_displayed_image') and self.current_displayed_image:
            save_btn = ctk.CTkButton(
                self.image_panel,
                text="💾",
                width=30,
                height=30,
                fg_color="gray20",
                hover_color="gray30",
                command=self.save_current_image_as_preset_example,
                border_spacing=0
            )
            save_btn.place(relx=0.80, rely=0.95, anchor="se")
            Tooltip(save_btn, "Save as Example Image")

    def save_current_image_as_preset_example(self):
        """Save the currently displayed image as the preset's example image"""
        if not hasattr(self, 'current_displayed_image') or not self.current_displayed_image:
            return
            
        if not self.current_preset_data or not self.current_engine:
            return

        try:
            # Determine filename
            current_example = self.current_preset_data.get("example_image", "")
            
            # If no example image set, or it's a placeholder, use preset name
            if not current_example or "_placeholders" in current_example or "/" in current_example:
                # Use preset filename base + .png
                if hasattr(self, 'current_preset_filename'):
                    base_name = os.path.splitext(self.current_preset_filename)[0]
                    target_filename = f"{base_name}.png"
                else:
                    target_filename = "preset_image.png" # Fallback
            else:
                target_filename = current_example
                
            # Ensure target directory exists
            engine_dir = os.path.join(PRESETS_DIR, self.current_engine)
            if not os.path.exists(engine_dir):
                os.makedirs(engine_dir)
                
            target_path = os.path.join(engine_dir, target_filename)
            
            # Save the ORIGINAL image (before resizing/corners if possible, but we only have displayed one here)
            # Ideally we should store the original pasted image. 
            # For now, we'll save the displayed image (which might be resized/cornered).
            # Wait, saving cornered image is bad for re-use. 
            # We should store the raw pasted image in self.current_raw_image
            
            img_to_save = getattr(self, 'current_raw_image', self.current_displayed_image)
            img_to_save.save(target_path)
            
            # Update preset data if filename changed
            if current_example != target_filename:
                self.current_preset_data["example_image"] = target_filename
                
                # Save JSON
                if hasattr(self, 'current_preset_filename'):
                    json_path = os.path.join(engine_dir, self.current_preset_filename)
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(self.current_preset_data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Saved", f"Image saved as {target_filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {e}")

    def display_example_image(self):
        """Display example image in the dedicated image panel"""
        # Clear previous image
        for widget in self.image_panel.winfo_children():
            widget.destroy()
            
        self.current_displayed_image = None
        self.current_raw_image = None # Reset raw image
        
        if not self.current_preset_data:
            self.image_placeholder = ctk.CTkLabel(self.image_panel, text="No Image", text_color="gray")
            self.image_placeholder.grid(row=0, column=0, sticky="nsew")
            self.add_image_overlay_buttons()
            return
            
        example_image = self.current_preset_data.get("example_image", "")
        image_path = None
        
        if example_image:
            # Check preset folder first
            path1 = os.path.join(PRESETS_DIR, self.current_engine, example_image)
            if os.path.exists(path1):
                image_path = path1
            else:
                # Check shared placeholders
                path2 = os.path.join(PRESETS_DIR, "_placeholders", example_image)
                if os.path.exists(path2):
                    image_path = path2
        
        if image_path:
            try:
                # Load and resize image to fit panel
                img = Image.open(image_path)
                self.current_raw_image = img.copy() # Store raw
                
                # Calculate aspect ratio to fit within panel (approx 250px width)
                target_w = 250
                ratio = target_w / img.width
                target_h = int(img.height * ratio)
                
                # Resize first
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                self.current_displayed_image = img # Store resized
                
                # Add rounded corners
                img = self.add_corners(img, 15) # Radius 15 to match card style
                
                img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(target_w, target_h))
                
                img_label = ctk.CTkLabel(self.image_panel, image=img_ctk, text="")
                img_label.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
                
                # Re-add paste button on top
                self.add_image_overlay_buttons()
                return
            except Exception as e:
                print(f"Error loading image: {e}")
        
        # Fallback if no image or error
        self.image_placeholder = ctk.CTkLabel(self.image_panel, text="No Image", text_color="gray")
        self.image_placeholder.grid(row=0, column=0, sticky="nsew")
        self.add_image_overlay_buttons()
