import os
import sys
import ctypes
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import customtkinter as ctk
from PIL import Image, ImageTk
import cv2
import numpy as np

current_dir = Path(__file__).resolve().parent
engine_dir = current_dir.parents[1]
if str(engine_dir) not in sys.path:
    sys.path.insert(0, str(engine_dir))

from core.logger import setup_logger
from utils.i18n import _

logger = setup_logger("doc_scan_gui")


@dataclass
class ImageItem:
    filepath: Path
    original_cv: np.ndarray
    thumbnail_photo: ImageTk.PhotoImage = None
    original_pts_cv: np.ndarray = None
    working_cv: np.ndarray = None
    warped_cv: np.ndarray = None
    filtered_cv: np.ndarray = None
    is_warped: bool = False
    filter_type: str = "orig" # "orig", "bw", "magic"

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped

def find_document_contour(image_cv, display_size=(800, 600)):
    ratio = image_cv.shape[0] / 500.0
    orig = image_cv.copy()
    image = cv2.resize(image_cv.copy(), (int(image_cv.shape[1]/ratio), 500))

    gray = cv2.cvtColor(image, cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape)==3 else image)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 75, 200)

    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    screenCnt = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            screenCnt = approx
            break

    h, w = image_cv.shape[:2]
    
    if screenCnt is None:
        padding = 50
        pts = np.array([
            [padding, padding],
            [w - padding, padding],
            [w - padding, h - padding],
            [padding, h - padding]
        ], dtype="float32")
        return pts, False
    else:
        pts = screenCnt.reshape(4, 2) * ratio
        return pts.astype("float32"), True

def apply_image_filter(img, filter_type):
    if img is None: return None
    if filter_type == "orig":
        return img.copy()
    elif filter_type == "bw":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Using adaptive threshold for clean document B&W
        bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10)
        return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
    elif filter_type == "magic":
        # Magic Color: enhance contrast and saturation
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        
        # apply CLAHE to Value channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        v_eq = clahe.apply(v)
        
        # Increase saturation by 20%
        s_eq = cv2.add(s, 50)
        
        hsv_eq = cv2.merge((h, s_eq, v_eq))
        colored = cv2.cvtColor(hsv_eq, cv2.HSV2BGR)
        
        # Sharpening
        kernel = np.array([[0,-1,0], [-1,5,-1], [0,-1,0]])
        sharpened = cv2.filter2D(colored, -1, kernel)
        return sharpened
    return img

def deskew_image(image):
    # Deskew algorithm using HoughLines
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

class DocScanGUI(ctk.CTk):
    def __init__(self, targets):
        super().__init__()

        self.title(_("doc_scan.title"))
        self.geometry("1100x750")

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.items: List[ImageItem] = []
        self.current_idx = -1
        
        # Zooming and Panning state
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0

        # UI State for points
        self.corner_points_canvas = []
        self.dragged_point_idx = None
        self.point_radius = 10
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        self.quality_var = ctk.StringVar(value=_("doc_scan.quality_med"))
        self.filter_var = ctk.StringVar(value="orig")
        
        self.rapid_ocr = None
        
        self.setup_ui()
        self.bind("<Configure>", self.on_resize)
        
        self.load_images(targets)

    def setup_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=5)
        
        lbl_header = ctk.CTkLabel(
            header_frame, 
            text=_("doc_scan.header"), 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_header.pack(side="left")

        # Main Layout
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Thumbnail Scroll Frame (Left)
        self.thumb_frame = ctk.CTkScrollableFrame(main_frame, width=150)
        self.thumb_frame.pack(side="left", fill="y", padx=(0, 10))

        # Canvas Frame (Middle)
        self.canvas_frame = ctk.CTkFrame(main_frame)
        self.canvas_frame.pack(side="left", fill="both", expand=True, padx=0)

        import tkinter as tk
        bg_col = "#EBEBEB" if ctk.get_appearance_mode() == "Light" else "#2b2b2b"
        self.canvas = tk.Canvas(self.canvas_frame, bg=bg_col, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.canvas.bind("<ButtonPress-1>", self.on_press_left)
        self.canvas.bind("<B1-Motion>", self.on_drag_left)
        self.canvas.bind("<ButtonRelease-1>", self.on_release_left)
        self.canvas.bind("<ButtonPress-2>", self.on_press_mid)
        self.canvas.bind("<B2-Motion>", self.on_drag_mid)
        self.canvas.bind("<ButtonRelease-2>", self.on_release_mid)
        self.canvas.bind("<ButtonPress-3>", self.on_press_mid)
        self.canvas.bind("<B3-Motion>", self.on_drag_mid)
        self.canvas.bind("<ButtonRelease-3>", self.on_release_mid)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        # Controls Frame (Right)
        control_frame = ctk.CTkFrame(main_frame, width=240)
        control_frame.pack(side="right", fill="y", padx=(10, 0))
        
        # Tools
        tool_lbl = ctk.CTkLabel(control_frame, text=_("doc_scan.tools"), font=ctk.CTkFont(weight="bold"))
        tool_lbl.pack(pady=(10, 5))
        
        rot_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        rot_frame.pack(fill="x", padx=10, pady=5)
        self.btn_rot_l = ctk.CTkButton(rot_frame, text=_("doc_scan.rotate_left"), command=lambda: self.rotate_image(-90), width=100)
        self.btn_rot_l.pack(side="left", padx=(0, 5))
        self.btn_rot_r = ctk.CTkButton(rot_frame, text=_("doc_scan.rotate_right"), command=lambda: self.rotate_image(90), width=100)
        self.btn_rot_r.pack(side="right")
        
        self.btn_reset = ctk.CTkButton(control_frame, text=_("doc_scan.reset_btn"), command=self.reset_image)
        self.btn_reset.pack(fill="x", padx=10, pady=5)
        
        self.btn_warp = ctk.CTkButton(control_frame, text=_("doc_scan.warp_btn"), command=self.process_warp)
        self.btn_warp.pack(fill="x", padx=10, pady=(15, 5))
        
        # Filters
        filter_lbl = ctk.CTkLabel(control_frame, text=_("doc_scan.filters"), font=ctk.CTkFont(weight="bold"))
        filter_lbl.pack(pady=(15, 5))
        
        self.rad_orig = ctk.CTkRadioButton(control_frame, text=_("doc_scan.filter_orig"), variable=self.filter_var, value="orig", command=self.on_filter_changed)
        self.rad_orig.pack(padx=20, pady=5, anchor="w")
        self.rad_bw = ctk.CTkRadioButton(control_frame, text=_("doc_scan.filter_bw"), variable=self.filter_var, value="bw", command=self.on_filter_changed)
        self.rad_bw.pack(padx=20, pady=5, anchor="w")
        self.rad_magic = ctk.CTkRadioButton(control_frame, text=_("doc_scan.filter_magic"), variable=self.filter_var, value="magic", command=self.on_filter_changed)
        self.rad_magic.pack(padx=20, pady=5, anchor="w")
        
        self.btn_deskew = ctk.CTkButton(control_frame, text=_("doc_scan.deskew_btn"), command=self.apply_deskew, fg_color="#E67E22", hover_color="#D35400")
        self.btn_deskew.pack(fill="x", padx=10, pady=10)
        
        self.btn_ocr = ctk.CTkButton(control_frame, text=_("doc_scan.ocr_btn"), command=self.run_ocr, fg_color="#8E44AD", hover_color="#732D91")
        self.btn_ocr.pack(fill="x", padx=10, pady=5)
        
        # Saving
        save_lbl = ctk.CTkLabel(control_frame, text=_("doc_scan.export_settings"), font=ctk.CTkFont(weight="bold"))
        save_lbl.pack(pady=(20, 5))
        
        self.opt_quality = ctk.CTkOptionMenu(
            control_frame, 
            values=[_("doc_scan.quality_high"), _("doc_scan.quality_med"), _("doc_scan.quality_low")],
            variable=self.quality_var
        )
        self.opt_quality.pack(fill="x", padx=10, pady=5)

        self.btn_save_png = ctk.CTkButton(control_frame, text=_("doc_scan.save_png"), command=lambda: self.save_result("png"))
        self.btn_save_png.pack(fill="x", padx=10, pady=5)
        
        self.btn_save_pdf = ctk.CTkButton(control_frame, text=_("doc_scan.save_pdf").format(count=0), command=lambda: self.save_result("pdf"), fg_color="#27AE60", hover_color="#2ECC71")
        self.btn_save_pdf.pack(fill="x", padx=10, pady=10)

    def load_images(self, targets):
        for path in targets:
            p = Path(path)
            if not p.exists(): continue
            
            stream = open(p, "rb")
            bytes_array = bytearray(stream.read())
            numpy_array = np.asarray(bytes_array, dtype=np.uint8)
            cv_img = cv2.imdecode(numpy_array, cv2.IMREAD_COLOR)
            
            if cv_img is None: continue
            
            # create thumb
            thumb_size = 120
            h, w = cv_img.shape[:2]
            scale = thumb_size / max(w, h)
            t_w, t_h = int(w * scale), int(h * scale)
            thumb_cv = cv2.resize(cv_img, (t_w, t_h))
            thumb_rgb = cv2.cvtColor(thumb_cv, cv2.COLOR_BGR2RGB)
            thumb_pil = Image.fromarray(thumb_rgb)
            thumb_photo = ImageTk.PhotoImage(image=thumb_pil)
            
            pts, success = find_document_contour(cv_img)
            
            item = ImageItem(
                filepath=p,
                original_cv=cv_img,
                thumbnail_photo=thumb_photo,
                original_pts_cv=pts,
                working_cv=cv_img.copy()
            )
            self.items.append(item)
            
            idx = len(self.items) - 1
            btn = ctk.CTkButton(
                self.thumb_frame, 
                image=thumb_photo, 
                text="",
                width=120, height=120,
                command=lambda i=idx: self.select_item(i)
            )
            btn.pack(pady=5)
            
        if self.items:
            self.btn_save_pdf.configure(text=_("doc_scan.save_pdf").format(count=len(self.items)))
            self.select_item(0)

    def get_current(self) -> Optional[ImageItem]:
        if 0 <= self.current_idx < len(self.items):
            return self.items[self.current_idx]
        return None

    def select_item(self, idx):
        self.current_idx = idx
        item = self.get_current()
        if not item: return
        
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.filter_var.set(item.filter_type)
        self.update_ui_state()
        self.update_canvas(resize=True)

    def update_ui_state(self):
        item = self.get_current()
        if not item: return
        
        if item.is_warped:
            self.btn_warp.configure(state="disabled")
            self.btn_rot_l.configure(state="disabled")
            self.btn_rot_r.configure(state="disabled")
            self.rad_orig.configure(state="normal")
            self.rad_bw.configure(state="normal")
            self.rad_magic.configure(state="normal")
            self.btn_deskew.configure(state="normal")
            self.btn_ocr.configure(state="normal")
        else:
            self.btn_warp.configure(state="normal")
            self.btn_rot_l.configure(state="normal")
            self.btn_rot_r.configure(state="normal")
            self.rad_orig.configure(state="disabled")
            self.rad_bw.configure(state="disabled")
            self.rad_magic.configure(state="disabled")
            self.btn_deskew.configure(state="disabled")
            self.btn_ocr.configure(state="disabled")

    def rotate_image(self, angle):
        item = self.get_current()
        if not item or item.is_warped: return
            
        if angle == 90:
            item.working_cv = cv2.rotate(item.working_cv, cv2.ROTATE_90_CLOCKWISE)
        elif angle == -90:
            item.working_cv = cv2.rotate(item.working_cv, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
        pts, _ = find_document_contour(item.working_cv)
        item.original_pts_cv = pts
        
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update_canvas(resize=True)

    def reset_image(self):
        item = self.get_current()
        if not item: return
        
        item.working_cv = item.original_cv.copy()
        pts, _ = find_document_contour(item.working_cv)
        item.original_pts_cv = pts
        item.warped_cv = None
        item.filtered_cv = None
        item.is_warped = False
        item.filter_type = "orig"
        self.filter_var.set("orig")
        
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update_ui_state()
        self.update_canvas(resize=True)

    def _cv_to_canvas(self, cv_x, cv_y):
        cx = (cv_x * self.scale_factor * self.zoom_factor) + self.offset_x + self.pan_x
        cy = (cv_y * self.scale_factor * self.zoom_factor) + self.offset_y + self.pan_y
        return cx, cy

    def _canvas_to_cv(self, cx, cy):
        cv_x = (cx - self.offset_x - self.pan_x) / (self.scale_factor * self.zoom_factor)
        cv_y = (cy - self.offset_y - self.pan_y) / (self.scale_factor * self.zoom_factor)
        return cv_x, cv_y

    def update_canvas(self, resize=False):
        item = self.get_current()
        if not item: return
        
        img_to_show = item.filtered_cv if item.is_warped else item.working_cv
        if img_to_show is None: return

        self.canvas.delete("all")
        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()
        if c_width <= 1 or c_height <= 1: return
            
        img_h, img_w = img_to_show.shape[:2]
        if resize:
            scale_w = c_width / img_w
            scale_h = c_height / img_h
            self.scale_factor = min(scale_w, scale_h) * 0.95
            self.offset_x = (c_width - (img_w * self.scale_factor)) / 2
            self.offset_y = (c_height - (img_h * self.scale_factor)) / 2
        
        new_w = int(img_w * self.scale_factor * self.zoom_factor)
        new_h = int(img_h * self.scale_factor * self.zoom_factor)
        if new_w <= 0 or new_h <= 0 or new_w > 10000 or new_h > 10000: return
            
        rgb_image = cv2.cvtColor(img_to_show, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_image).resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.photo_image = ImageTk.PhotoImage(image=pil_img)
        self.canvas.create_image(self.offset_x + self.pan_x, self.offset_y + self.pan_y, anchor="nw", image=self.photo_image)
        
        if not item.is_warped and item.original_pts_cv is not None:
            self.corner_points_canvas = []
            for pt in item.original_pts_cv:
                self.corner_points_canvas.append(list(self._cv_to_canvas(pt[0], pt[1])))
            self.draw_overlay()

    def draw_overlay(self):
        self.canvas.delete("overlay")
        if not self.corner_points_canvas or len(self.corner_points_canvas) != 4: return
        pts = self.corner_points_canvas
        ordered = order_points(np.array(pts))
        
        for i in range(4):
            pt1 = ordered[i]
            pt2 = ordered[(i+1)%4]
            self.canvas.create_line(pt1[0], pt1[1], pt2[0], pt2[1], fill="#00ff00", width=max(1, int(2 * self.zoom_factor)), tags="overlay")
            
        r = self.point_radius
        for pt in self.corner_points_canvas:
            x, y = pt
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="#ff0000", outline="#ffffff", width=2, tags="overlay")

    def on_resize(self, event):
        if event.widget == self.canvas:
            self.update_canvas(resize=True if self.zoom_factor == 1.0 else False)

    def on_press_left(self, event):
        item = self.get_current()
        if not item or item.is_warped or not self.corner_points_canvas: return
            
        x, y = event.x, event.y
        r = self.point_radius + 5
        min_dist = float('inf')
        self.dragged_point_idx = None
        
        for i, pt in enumerate(self.corner_points_canvas):
            dist = math.hypot(pt[0] - x, pt[1] - y)
            if dist < r and dist < min_dist:
                min_dist = dist
                self.dragged_point_idx = i

    def on_drag_left(self, event):
        item = self.get_current()
        if self.dragged_point_idx is not None and not item.is_warped:
            self.corner_points_canvas[self.dragged_point_idx] = [event.x, event.y]
            cv_x, cv_y = self._canvas_to_cv(event.x, event.y)
            
            h, w = item.working_cv.shape[:2]
            cv_x = max(0, min(w, cv_x))
            cv_y = max(0, min(h, cv_y))
            
            item.original_pts_cv[self.dragged_point_idx] = [cv_x, cv_y]
            self.corner_points_canvas[self.dragged_point_idx] = list(self._cv_to_canvas(cv_x, cv_y))
            self.draw_overlay()

    def on_release_left(self, event):
        self.dragged_point_idx = None
        
    def on_press_mid(self, event):
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def on_drag_mid(self, event):
        if self.is_panning:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            self.pan_x += dx
            self.pan_y += dy
            self.pan_start_x = event.x
            self.pan_start_y = event.y
            self.update_canvas()

    def on_release_mid(self, event):
        self.is_panning = False
        
    def on_mouse_wheel(self, event):
        cx, cy = event.x, event.y
        cv_x, cv_y = self._canvas_to_cv(cx, cy)
        
        zoom_step = 1.2
        if event.delta > 0: self.zoom_factor *= zoom_step
        else: self.zoom_factor /= zoom_step
        self.zoom_factor = max(0.5, min(self.zoom_factor, 10.0))
        
        self.pan_x = cx - (cv_x * self.scale_factor * self.zoom_factor) - self.offset_x
        self.pan_y = cy - (cv_y * self.scale_factor * self.zoom_factor) - self.offset_y
        self.update_canvas()

    def process_warp(self):
        item = self.get_current()
        if not item or item.original_pts_cv is None: return

        warped = four_point_transform(item.working_cv, item.original_pts_cv)
        item.warped_cv = warped
        item.is_warped = True
        item.filter_type = self.filter_var.get()
        item.filtered_cv = apply_image_filter(item.warped_cv, item.filter_type)
        
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update_ui_state()
        self.update_canvas(resize=True)

    def on_filter_changed(self):
        item = self.get_current()
        if not item or not item.is_warped: return
        item.filter_type = self.filter_var.get()
        item.filtered_cv = apply_image_filter(item.warped_cv, item.filter_type)
        self.update_canvas()

    def apply_deskew(self):
        item = self.get_current()
        if not item or not item.is_warped: return
        # Apply to raw warped, then re-filter
        item.warped_cv = deskew_image(item.warped_cv)
        item.filtered_cv = apply_image_filter(item.warped_cv, item.filter_type)
        self.update_canvas(resize=True)

    def run_ocr(self):
        item = self.get_current()
        if not item or not item.is_warped: return
        import tkinter.messagebox as msgbox
        
        try:
            from rapidocr_onnxruntime import RapidOCR
            if self.rapid_ocr is None:
                self.rapid_ocr = RapidOCR()
            
            result, elapse = self.rapid_ocr(item.filtered_cv)
            if result:
                texts = [res[1] for res in result]
                full_text = "\n".join(texts)
                
                # Copy to clipboard
                self.clipboard_clear()
                self.clipboard_append(full_text)
                self.update() # necessary for clipboard
                
                msgbox.showinfo(_("doc_scan.ocr_title"), _("doc_scan.ocr_tooltip").format(text=full_text[:50] + "..."))
            else:
                msgbox.showwarning(_("doc_scan.ocr_title"), _("doc_scan.ocr_failed"))
        except ImportError:
            msgbox.showerror(_("doc_scan.error_title"), _("doc_scan.ocr_not_installed"))
        except Exception as e:
            msgbox.showerror(_("doc_scan.error_title"), str(e))

    def _prepare_export_image(self, item: ImageItem):
        if not item.is_warped:
            # Auto warp if they haven't manually
            w = four_point_transform(item.working_cv, item.original_pts_cv)
            export_img = apply_image_filter(w, item.filter_type)
        else:
            export_img = item.filtered_cv.copy()
            
        q_str = self.quality_var.get()
        h, w = export_img.shape[:2]
        if q_str == _("doc_scan.quality_med") and max(w, h) > 2000:
            scale = 2000 / max(w, h)
            export_img = cv2.resize(export_img, (int(w*scale), int(h*scale)))
        elif q_str == _("doc_scan.quality_low") and max(w, h) > 1000:
            scale = 1000 / max(w, h)
            export_img = cv2.resize(export_img, (int(w*scale), int(h*scale)))
        return export_img

    def save_result(self, format_type):
        if not self.items: return
        import tkinter.messagebox as msgbox
        
        orig_p = self.items[0].filepath
        try:
            if format_type == "png":
                # Save just current
                item = self.get_current()
                if not item: return
                export_img = self._prepare_export_image(item)
                out_p = orig_p.with_stem(f"{orig_p.stem}_scanned").with_suffix(".png")
                cv2.imencode('.png', export_img)[1].tofile(out_p)
                msgbox.showinfo(_("common.success"), _("doc_scan.saved_fmt").format(dest=out_p.name))
                self.quit()
                
            elif format_type == "pdf":
                # Batch save all
                out_p = orig_p.with_stem(f"{orig_p.stem}_batch_scanned").with_suffix(".pdf")
                pil_images = []
                for item in self.items:
                    export_img = self._prepare_export_image(item)
                    rgb_image = cv2.cvtColor(export_img, cv2.COLOR_BGR2RGB)
                    pil_images.append(Image.fromarray(rgb_image))
                
                if pil_images:
                    pil_images[0].save(out_p, "PDF", resolution=100.0, save_all=True, append_images=pil_images[1:])
                    msgbox.showinfo(_("common.success"), _("doc_scan.saved_fmt").format(dest=out_p.name))
                    self.quit()
                    
        except Exception as e:
            logger.error(f"Save failed: {e}")
            msgbox.showerror(_("common.error"), str(e))

def main():
    if sys.platform == 'win32':
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        
    targets = [t for t in sys.argv[1:] if Path(t).exists()]
    app = DocScanGUI(targets)
    app.mainloop()

if __name__ == "__main__":
    main()

