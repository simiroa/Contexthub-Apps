"""
Gemini Image Tools - PBR Map Generation Module
CV2-based PBR texture map generation functions.
"""
import cv2
import numpy as np


def generate_normal_map(img, strength=1.0):
    """Generate a normal map from an image using Sobel gradients."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    x_grad = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    y_grad = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    z = np.ones_like(x_grad) * (1.0 / strength)
    normal = np.dstack((-x_grad, -y_grad, z))
    norm = np.linalg.norm(normal, axis=2)
    normal = normal / norm[:, :, np.newaxis]
    normal = ((normal + 1) * 0.5 * 255).astype(np.uint8)
    return cv2.cvtColor(normal, cv2.COLOR_RGB2BGR)


def generate_roughness_map(img, invert=False, contrast=1.0):
    """Generate a roughness map (grayscale) from an image."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if invert:
        gray = 255 - gray
    if contrast != 1.0:
        f = 131 * (contrast + 127) / (127 * (131 - contrast))
        alpha_c = f
        gamma_c = 127 * (1 - f)
        gray = cv2.addWeighted(gray, alpha_c, gray, 0, gamma_c)
    return gray


def generate_displacement_map(img):
    """Generate a displacement/height map (grayscale) from an image."""
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def generate_occlusion_map(img, strength=1.0):
    """Generate an ambient occlusion map from an image."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    invGamma = 1.0 / (0.5 * strength)
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(gray, table)


def generate_metallic_map(img, strength=1.0):
    """Generate a metallic map from an image."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return (gray * 0.2 * strength).astype(np.uint8)


def make_tileable_synthesis(img, overlap=0.15):
    """Make an image tileable using synthesis blending."""
    h, w = img.shape[:2]
    shift_x = w // 2
    shift_y = h // 2
    img_roll = np.roll(img, shift_x, axis=1)
    img_roll = np.roll(img_roll, shift_y, axis=0)
    mask = np.zeros((h, w), dtype=np.float32)
    sw = int(w * overlap)
    sh = int(h * overlap)
    img_blur = cv2.GaussianBlur(img_roll, (21, 21), 0)
    cv2.line(mask, (w//2, 0), (w//2, h), 1.0, sw)
    cv2.line(mask, (0, h//2), (w, h//2), 1.0, sh)
    mask = cv2.GaussianBlur(mask, (21, 21), 0)
    mask_3c = np.dstack((mask, mask, mask))
    res = (img_roll.astype(np.float32) * (1.0 - mask_3c) + img_blur.astype(np.float32) * mask_3c).astype(np.uint8)
    return res
