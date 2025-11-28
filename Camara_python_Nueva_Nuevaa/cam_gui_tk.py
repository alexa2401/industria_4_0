# -*- coding: utf-8 -*-
"""
CamDiff GUI (Tkinter) - Python 3.13 - Versión Optimizada para 5S
Sistema SENSIBLE para detectar mejor las herramientas
"""

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# ---- MQTT ----
import json
import paho.mqtt.client as mqtt

# ---------- Utilidades ----------
def ensure_odd(x: int) -> int:
    return x if x % 2 == 1 else x + 1

def color_for_pct(pct: float) -> str:
    """
    Colores para sistema 5S de herramientas:
      0 - 15  -> verde (todo OK)
      15 - 35 -> amarillo (advertencia)
      35 - 60 -> naranja (falta herramienta)
      > 60    -> rojo (faltan múltiples)
    """
    if pct <= 15.0:
        return "#2ecc71"   # verde
    elif pct <= 35.0:
        return "#f1c40f"   # amarillo
    elif pct <= 60.0:
        return "#e67e22"   # naranja
    else:
        return "#e74c3c"   # rojo

def bgr_to_tk(frame, max_w=None):
    h, w = frame.shape[:2]
    if max_w and w > max_w:
        s = max_w / float(w)
        frame = cv2.resize(frame, (int(w*s), int(h*s)))
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    return ImageTk.PhotoImage(pil)

def gray_to_tk(gray, max_w=None):
    if len(gray.shape) != 2:
        raise ValueError("Se esperaba imagen en escala de grises.")
    h, w = gray.shape
    if max_w and w > max_w:
        s = max_w / float(w)
        gray = cv2.resize(gray, (int(w*s), int(h*s)))
    pil = Image.fromarray(gray)
    return ImageTk.PhotoImage(pil.convert("L"))

# ---------- SSIM ----------
def ssim_map(gray1, gray2, ksize=11, sigma=1.5):
    k = cv2.getGaussianKernel(ksize, sigma)
    w = k @ k.T
    mu1 = cv2.filter2D(gray1, -1, w)
    mu2 = cv2.filter2D(gray2, -1, w)
    mu1_sq, mu2_sq, mu1_mu2 = mu1*mu1, mu2*mu2, mu1*mu2
    sigma1_sq = cv2.filter2D(gray1*gray1, -1, w) - mu1_sq
    sigma2_sq = cv2.filter2D(gray2*gray2, -1, w) - mu2_sq
    sigma12   = cv2.filter2D(gray1*gray2, -1, w) - mu1_mu2
    C1, C2 = (0.01*255)**2, (0.03*255)**2
    num = (2*mu1_mu2 + C1)*(2*sigma12 + C2)
    den = (mu1_sq + mu2_sq + C1)*(sigma1_sq + sigma2_sq + C2)
    ssim = num / (den + 1e-12)
    return np.clip(ssim, 0, 1)

# ---------- Alineado ECC ----------
def align_ecc(img1, img2):
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    g1 = cv2.GaussianBlur(g1, (5,5), 0)
    g2 = cv2.GaussianBlur(g2, (5,5), 0)
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-5)
        _, warp = cv2.findTransformECC(g1, g2, warp, cv2.MOTION_EUCLIDEAN, criteria)
        aligned = cv2.warpAffine(img2, warp, (img2.shape[1], img2.shape[0]),
                                 flags=cv2.INTER_LINEAR+cv2.WARP_INVERSE_MAP,
                                 borderMode=cv2.BORDER_REPLICATE)
        return aligned, True
    except cv2.error as e:
        print(f"Error en alineado ECC: {e}")
        return img2, False
    except Exception as e:
        print(f"Error inesperado en alineado: {e}")
        return img2, False

# ---------- Comparaciones base ----------
def compare_absdiff(img1, img2, blur=5, thresh=30, morph=5):
    if img1.shape != img2.shape:
        raise ValueError("Tamaños distintos.")
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    if blur and blur > 1:
        k = blur if blur % 2 else blur + 1
        g1 = cv2.GaussianBlur(g1, (k, k), 0)
        g2 = cv2.GaussianBlur(g2, (k, k), 0)
    diff = cv2.absdiff(g1, g2)
    _, mask = cv2.threshold(diff, thresh, 255, cv2.THRESH_BINARY)
    if morph and morph > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, 1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, 1)
    diff_col = cv2.cvtColor(diff, cv2.COLOR_GRAY2BGR)
    diff_col[mask > 0] = [0, 0, 255]
    changed = int(np.sum(mask > 0))
    pct = (changed / max(mask.size, 1)) * 100.0
    return mask, diff_col, changed, pct

def compare_ssim(img1, img2, blur=5, thresh=30, morph=5):
    if img1.shape != img2.shape:
        raise ValueError("Tamaños distintos.")
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    if blur and blur > 1:
        k = blur if blur % 2 else blur + 1
        g1 = cv2.GaussianBlur(g1, (k, k), 0)
        g2 = cv2.GaussianBlur(g2, (k, k), 0)

    ssim = ssim_map(g1.astype(np.float32), g2.astype(np.float32))
    change = 1.0 - ssim
    thr = np.clip(thresh / 255.0, 0.0, 1.0)
    mask = (change >= thr).astype(np.uint8) * 255

    if morph and morph > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, 1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, 1)

    heat = (change * 255).astype(np.uint8)
    heat_col = cv2.applyColorMap(heat, cv2.COLORMAP_JET)

    red_img = np.zeros_like(heat_col, dtype=np.uint8); red_img[:] = (0, 0, 255)
    blended = cv2.addWeighted(heat_col, 0.6, red_img, 0.4, 0)
    heat_col[mask > 0] = blended[mask > 0]

    changed = int(np.sum(mask > 0))
    pct = float(change.mean() * 100.0)
    return mask, heat_col, changed, pct

def compare_edges(img1, img2, blur=5, thresh=30, morph=5):
    if img1.shape != img2.shape:
        raise ValueError("Tamaños distintos.")
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    if blur and blur > 1:
        k = blur if blur % 2 else blur + 1
        g1 = cv2.GaussianBlur(g1, (k, k), 0)
        g2 = cv2.GaussianBlur(g2, (k, k), 0)
    e1 = cv2.Canny(g1, 50, 150)
    e2 = cv2.Canny(g2, 50, 150)
    diff_edges = cv2.bitwise_xor(e1, e2)
    if morph and morph > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        diff_edges = cv2.morphologyEx(diff_edges, cv2.MORPH_CLOSE, kernel, 1)
    mask = (diff_edges > 0).astype(np.uint8) * 255
    diff_col = cv2.cvtColor(g2, cv2.COLOR_GRAY2BGR); diff_col[mask > 0] = [0, 0, 255]
    changed = int(np.sum(mask > 0))
    pct = (changed / max(mask.size, 1)) * 100.0
    return mask, diff_col, changed, pct

# ========== Contador de objetos MÁS SENSIBLE ==========
def count_tools_in_image(img, blur=5, thresh=30, morph=5, min_area=1500):
    """
    Cuenta las herramientas/objetos detectados en una imagen.
    VERSIÓN MÁS SENSIBLE para mejor detección.
    """
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    if blur and blur > 1:
        k = blur if blur % 2 else blur + 1
        g = cv2.GaussianBlur(g, (k,k), 0)
    
    # Ecualización adaptativa MÁS AGRESIVA
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))  # Aumentado de 2.0 a 3.0
    g = clahe.apply(g)
    
    # Umbralización adaptativa MÁS SENSIBLE
    binary = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 15, 5)  # Reducido de 21,10 a 15,5
    
    # Morfología MENOS agresiva para no perder objetos
    if morph and morph > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)  # 1 vez, no 2
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Limpiar bordes (reducido)
    border = 15  # Antes era 20
    binary[:border, :] = 0
    binary[-border:, :] = 0
    binary[:, :border] = 0
    binary[:, -border:] = 0
    
    # Encontrar contornos
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    valid_tools = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        
        x, y, w, h = cv2.boundingRect(c)
        aspect_ratio = max(w, h) / max(min(w, h), 1)
        
        # Filtros MÁS PERMISIVOS
        if aspect_ratio > 8.0:  # Antes era 5.0
            continue
        
        # Compacidad más permisiva
        perimeter = cv2.arcLength(c, True)
        if perimeter > 0:
            compactness = 4 * np.pi * area / (perimeter ** 2)
            if compactness < 0.10:  # Antes era 0.15
                continue
        
        valid_tools.append(area)
    
    return len(valid_tools), valid_tools

# ---------- Detección MEJORADA y MÁS SENSIBLE ----------
def detect_added_removed_smart(img1, img2, blur=5, thresh=30, morph=5, min_area=1500,
                               tools_in_reference=None):
    """
    Versión MÁS SENSIBLE para detectar mejor las herramientas.
    """
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    
    # Blur reducido para más detalle
    if blur and blur > 1:
        k = blur if blur % 2 else blur + 1
        g1 = cv2.GaussianBlur(g1, (k,k), 0)
        g2 = cv2.GaussianBlur(g2, (k,k), 0)

    # Ecualización más agresiva
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    g1 = clahe.apply(g1)
    g2 = clahe.apply(g2)
    
    # Diferencias con signo
    pos = cv2.subtract(g2, g1)
    neg = cv2.subtract(g1, g2)

    # Umbral MÁS BAJO para mayor sensibilidad
    thr_loc = max(thresh, 30)  # Antes era 45

    _, add_mask = cv2.threshold(pos, thr_loc, 255, cv2.THRESH_BINARY)
    _, rem_mask = cv2.threshold(neg, thr_loc, 255, cv2.THRESH_BINARY)

    # Morfología MENOS agresiva
    if morph and morph > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        add_mask = cv2.morphologyEx(add_mask, cv2.MORPH_OPEN, kernel, iterations=1)  # 1 vez
        add_mask = cv2.morphologyEx(add_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        rem_mask = cv2.morphologyEx(rem_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        rem_mask = cv2.morphologyEx(rem_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    # Limpiar bordes (reducido)
    border = 15
    for m in (add_mask, rem_mask):
        m[:border, :] = 0
        m[-border:, :] = 0
        m[:, :border] = 0
        m[:, -border:] = 0

    overlay = img2.copy()

    def draw_regions(bin_mask, color_bgr, label):
        count = 0
        total_area = 0
        contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_contours = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area:
                continue
            
            x, y, w, h = cv2.boundingRect(c)
            aspect_ratio = max(w, h) / max(min(w, h), 1)
            
            # Más permisivo
            if aspect_ratio > 8.0:  # Antes 5.0
                continue
            
            perimeter = cv2.arcLength(c, True)
            if perimeter > 0:
                compactness = 4 * np.pi * area / (perimeter ** 2)
                if compactness < 0.10:  # Antes 0.15
                    continue
            
            valid_contours.append((c, area, x, y, w, h))
        
        for c, area, x, y, w, h in valid_contours:
            cv2.rectangle(overlay, (x, y), (x+w, y+h), color_bgr, 3)
            roi = overlay[y:y+h, x:x+w]
            tint = np.full_like(roi, color_bgr, dtype=np.uint8)
            cv2.addWeighted(tint, 0.3, roi, 0.7, 0, dst=roi)
            
            label_text = f"{label}"
            (text_w, text_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(overlay, (x, y-text_h-10), (x+text_w+4, y), color_bgr, -1)
            cv2.putText(overlay, label_text, (x+2, y-6), 
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.7, (255, 255, 255), 2, cv2.LINE_AA)
            count += 1
            total_area += area
        
        return count, total_area

    added, added_area = draw_regions(add_mask, (0, 255, 0), "Añadido")
    removed, removed_area = draw_regions(rem_mask, (255, 0, 0), "Removido")
    total_area = added_area + removed_area
    
    # ========== CÁLCULO INTELIGENTE DEL SCORE ==========
    tools_photo2, _ = count_tools_in_image(img2, blur=blur, thresh=thresh, 
                                           morph=morph, min_area=min_area)
    
    score_intelligent = 0.0
    
    if tools_in_reference is not None and tools_in_reference > 0:
        # Método 1: Basado en conteo
        tools_missing = max(0, tools_in_reference - tools_photo2)
        score_by_count = (tools_missing / tools_in_reference) * 100.0
        
        # Método 2: Basado en área (multiplicador aumentado)
        total_pixels = img1.shape[0] * img1.shape[1]
        pct_area = (total_area / float(total_pixels)) * 100.0
        score_by_area = pct_area * 12.0  # Aumentado de x10 a x12
        
        # Combinar (70% conteo, 30% área)
        score_intelligent = (score_by_count * 0.70) + (score_by_area * 0.30)
        
        # Limitar
        score_intelligent = min(score_intelligent, 100.0)
        
        # Garantizar score mínimo si hay objetos removidos
        if removed > 0:
            score_intelligent = max(score_intelligent, 20.0)  # Aumentado de 15 a 20
    else:
        # Fallback
        total_pixels = img1.shape[0] * img1.shape[1]
        pct_area = (total_area / float(total_pixels)) * 100.0
        score_intelligent = min(pct_area * 12.0, 100.0)
    
    return overlay, added, removed, total_area, score_intelligent, tools_photo2

# ---------- Ventana de comparación ----------
class ComparisonWindow(tk.Toplevel):
    def __init__(self, master, max_w=520):
        super().__init__(master)
        self.title("Comparación - Sistema 5S")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.max_w = max_w

        self.card = tk.Frame(self, bd=0, highlightthickness=0, bg="#eeeeee")
        self.card.pack(padx=10, pady=10, fill="both", expand=True)

        self.inner = tk.Frame(self.card, bg=self.card["bg"])
        self.inner.pack(padx=12, pady=12)

        for col, txt in enumerate(("Foto 1 (Referencia)", "Mask/Mapa")):
            tk.Label(self.inner, text=txt, font=("Segoe UI", 10, "bold"),
                     bg=self.inner["bg"]).grid(row=0, column=col, sticky="s")
        for col, txt in enumerate(("Foto 2 (Actual)", "Diferencias")):
            tk.Label(self.inner, text=txt, font=("Segoe UI", 10, "bold"),
                     bg=self.inner["bg"]).grid(row=2, column=col, sticky="s")

        self.lbl_f1 = tk.Label(self.inner, bg=self.inner["bg"]); self.lbl_f1.grid(row=1, column=0, padx=6, pady=4)
        self.lbl_mk = tk.Label(self.inner, bg=self.inner["bg"]); self.lbl_mk.grid(row=1, column=1, padx=6, pady=4)
        self.lbl_f2 = tk.Label(self.inner, bg=self.inner["bg"]); self.lbl_f2.grid(row=3, column=0, padx=6, pady=4)
        self.lbl_df = tk.Label(self.inner, bg=self.inner["bg"]); self.lbl_df.grid(row=3, column=1, padx=6, pady=4)

        self._img_refs = []

        self.txt = tk.Label(self, text="—", anchor="w", font=("Segoe UI", 9))
        self.txt.pack(fill="x", padx=10, pady=(0,10))

        tk.Button(self, text="Cerrar", command=self.on_close, font=("Segoe UI", 10))\
            .pack(pady=(0,10))

    def _apply_card_color(self, color: str):
        self.card.configure(bg=color)
        self.inner.configure(bg=color)
        for w in (self.lbl_f1, self.lbl_mk, self.lbl_f2, self.lbl_df):
            w.configure(bg=color)
        for child in self.inner.grid_slaves():
            if isinstance(child, tk.Label) and child not in (self.lbl_f1,self.lbl_mk,self.lbl_f2,self.lbl_df):
                child.configure(bg=color)

    def update_images(self, photo1_bgr, photo2_bgr, mask_gray_or_map,
                      diff_bgr, pct, changed, extra_txt=""):
        self._img_refs.clear()
        self._apply_card_color(color_for_pct(pct))

        im_f1 = bgr_to_tk(photo1_bgr, self.max_w)
        self._img_refs.append(im_f1)
        self.lbl_f1.configure(image=im_f1)

        if len(mask_gray_or_map.shape) == 2:
            im_mk = gray_to_tk(mask_gray_or_map, self.max_w)
        else:
            im_mk = bgr_to_tk(mask_gray_or_map, self.max_w)
        self._img_refs.append(im_mk)
        self.lbl_mk.configure(image=im_mk)

        im_f2 = bgr_to_tk(photo2_bgr, self.max_w)
        self._img_refs.append(im_f2)
        self.lbl_f2.configure(image=im_f2)

        im_df = bgr_to_tk(diff_bgr, self.max_w)
        self._img_refs.append(im_df)
        self.lbl_df.configure(image=im_df)

        base = f"Score Inteligente: {pct:.1f}%"
        self.txt.configure(text= base + (f"\n{extra_txt}" if extra_txt else ""))

    def on_close(self):
        self.destroy()

# ---------- App principal ----------
class CamDiffApp:
    def __init__(self, root):
        self.root = root
        root.title("CamDiff GUI - Sistema 5S Sensible")
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.preview_w = 900
        self.photo1 = None
        self.last_result = None
        self.outdir = Path("outputs")
        self.outdir.mkdir(parents=True, exist_ok=True)
        self.comp_win = None
        self.roi = None
        self.tools_in_reference = None

        # Vista previa
        self.preview_label = ttk.Label(root)
        self.preview_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Panel derecho con scroll
        canvas = tk.Canvas(root, width=280)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        panel = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=1, sticky="ns")
        scrollbar.grid(row=0, column=2, sticky="ns")
        
        canvas_frame = canvas.create_window((0, 0), window=panel, anchor="nw")
        
        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        panel.bind("<Configure>", configure_scroll)
        
        # Título
        ttk.Label(panel, text="🔧 Sistema 5S Sensible", font=("Segoe UI", 12, "bold"))\
            .grid(row=0, column=0, columnspan=2, pady=(0,8))
        
        # Botones principales
        ttk.Button(panel, text="📷 Tomar Foto 1 (Referencia)", command=self.take_photo1)\
            .grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(panel, text="🔍 Tomar Foto 2 y Comparar", command=self.take_photo2_compare)\
            .grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(panel, text="🔄 Reiniciar", command=self.reset)\
            .grid(row=3, column=0, sticky="ew", pady=2)
        self.save_btn = ttk.Button(panel, text="💾 Guardar",
                                   command=self.save_results, state="disabled")
        self.save_btn.grid(row=3, column=1, sticky="ew", pady=2)

        # Info de herramientas
        self.lbl_tools_ref = ttk.Label(panel, text="Herramientas en referencia: --", 
                                       font=("Segoe UI", 9, "bold"), foreground="#2c3e50")
        self.lbl_tools_ref.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8,2))

        # --- Cámara ---
        ttk.Separator(panel, orient='horizontal').grid(row=5, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(panel, text="📹 Cámara", font=("Segoe UI", 10, "bold"))\
            .grid(row=6, column=0, columnspan=2, sticky="w")
        self.var_cam_idx = tk.StringVar(value="0")
        self.combo_cam = ttk.Combobox(panel, textvariable=self.var_cam_idx,
                                      state="readonly", width=12)
        self.combo_cam.grid(row=7, column=0, columnspan=2, sticky="ew")
        self.combo_cam.bind("<<ComboboxSelected>>", lambda e: self.open_camera())
        ttk.Button(panel, text="Detectar cámaras", command=self.detect_and_fill)\
            .grid(row=8, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(panel, text="Conectar", command=self.open_camera)\
            .grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0,4))

        ttk.Label(panel, text="Resolución:")\
            .grid(row=10, column=0, sticky="w")
        self.var_res = tk.StringVar(value="1280x720")
        ttk.Combobox(panel,
                     values=["640x480","1280x720","1920x1080"],
                     textvariable=self.var_res, state="readonly", width=12)\
            .grid(row=10, column=1, sticky="e")

        # --- ROI ---
        ttk.Separator(panel, orient='horizontal').grid(row=11, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(panel, text="📦 Área de Caja", font=("Segoe UI", 10, "bold"))\
            .grid(row=12, column=0, columnspan=2, sticky="w")
        self.var_use_roi = tk.BooleanVar(value=False)
        ttk.Checkbutton(panel, text="Usar solo área definida",
                        variable=self.var_use_roi)\
            .grid(row=13, column=0, columnspan=2, sticky="w")
        ttk.Button(panel, text="Definir área de caja", command=self.define_roi)\
            .grid(row=14, column=0, columnspan=2, sticky="ew", pady=2)

        # --- Configuración ---
        ttk.Separator(panel, orient='horizontal').grid(row=15, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(panel, text="⚙️ Configuración", font=("Segoe UI", 10, "bold"))\
            .grid(row=16, column=0, columnspan=2, sticky="w")
        
        ttk.Label(panel, text="Modo de comparación:")\
            .grid(row=17, column=0, columnspan=2, sticky="w")
        self.var_mode = tk.StringVar(value="SSIM (mapa)")
        ttk.Combobox(panel,
                     values=["AbsDiff","SSIM (mapa)","Bordes (Canny)"],
                     textvariable=self.var_mode, state="readonly")\
            .grid(row=18, column=0, columnspan=2, sticky="ew", pady=2)

        self.var_align = tk.BooleanVar(value=True)
        ttk.Checkbutton(panel, text="✓ Alinear antes (ECC)",
                        variable=self.var_align)\
            .grid(row=19, column=0, columnspan=2, sticky="w")

        # Umbral - MÁS BAJO (más sensible)
        ttk.Label(panel, text="🎯 Sensibilidad (menor = más sensible):")\
            .grid(row=20, column=0, columnspan=2, sticky="w", pady=(8,0))
        self.var_thresh = tk.IntVar(value=35)  # Reducido de 50 a 35
        thresh_frame = ttk.Frame(panel)
        thresh_frame.grid(row=21, column=0, columnspan=2, sticky="ew")
        ttk.Scale(thresh_frame, from_=15, to=80, orient="horizontal",
                  variable=self.var_thresh)\
            .pack(side="left", fill="x", expand=True)
        self.lbl_thresh = ttk.Label(thresh_frame, text="35", width=4)
        self.lbl_thresh.pack(side="right")
        self.var_thresh.trace_add("write", lambda *_: self.lbl_thresh.configure(text=str(int(self.var_thresh.get()))))

        # Blur - REDUCIDO (más detalle)
        ttk.Label(panel, text="Suavizado (menos = más detalle):")\
            .grid(row=22, column=0, columnspan=2, sticky="w")
        self.var_blur = tk.IntVar(value=5)  # Reducido de 9 a 5
        blur_frame = ttk.Frame(panel)
        blur_frame.grid(row=23, column=0, columnspan=2, sticky="ew")
        ttk.Scale(blur_frame, from_=3, to=15, orient="horizontal",
                  variable=self.var_blur)\
            .pack(side="left", fill="x", expand=True)
        self.lbl_blur = ttk.Label(blur_frame, text="5", width=4)
        self.lbl_blur.pack(side="right")
        self.var_blur.trace_add("write", lambda *_: self.lbl_blur.configure(text=str(int(self.var_blur.get()))))

        # Morph - REDUCIDO (menos limpieza = más objetos)
        ttk.Label(panel, text="Limpieza de ruido:")\
            .grid(row=24, column=0, columnspan=2, sticky="w")
        self.var_morph = tk.IntVar(value=5)  # Reducido de 7 a 5
        morph_frame = ttk.Frame(panel)
        morph_frame.grid(row=25, column=0, columnspan=2, sticky="ew")
        ttk.Scale(morph_frame, from_=3, to=15, orient="horizontal",
                  variable=self.var_morph)\
            .pack(side="left", fill="x", expand=True)
        self.lbl_morph = ttk.Label(morph_frame, text="5", width=4)
        self.lbl_morph.pack(side="right")
        self.var_morph.trace_add("write", lambda *_: self.lbl_morph.configure(text=str(int(self.var_morph.get()))))

        # --- Detección de herramientas ---
        ttk.Separator(panel, orient='horizontal').grid(row=26, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(panel, text="🔧 Detección Inteligente", font=("Segoe UI", 10, "bold"))\
            .grid(row=27, column=0, columnspan=2, sticky="w")
        
        self.var_boxes = tk.BooleanVar(value=True)
        ttk.Checkbutton(panel, text="✓ Modo inteligente (recomendado)",
                        variable=self.var_boxes)\
            .grid(row=28, column=0, columnspan=2, sticky="w")

        # Área mínima - REDUCIDA (detecta herramientas más pequeñas)
        ttk.Label(panel, text="Tamaño mínimo herramienta (px²):")\
            .grid(row=29, column=0, columnspan=2, sticky="w", pady=(8,0))
        self.var_min_area = tk.IntVar(value=1500)  # Reducido de 2500 a 1500
        area_frame = ttk.Frame(panel)
        area_frame.grid(row=30, column=0, columnspan=2, sticky="ew")
        ttk.Scale(area_frame, from_=500, to=10000, orient="horizontal",
                  variable=self.var_min_area)\
            .pack(side="left", fill="x", expand=True)
        self.lbl_area = ttk.Label(area_frame, text="1500", width=6)
        self.lbl_area.pack(side="right")
        self.var_min_area.trace_add("write", lambda *_: self.lbl_area.configure(text=str(int(self.var_min_area.get()))))

        # Status
        ttk.Separator(panel, orient='horizontal').grid(row=31, column=0, columnspan=2, sticky="ew", pady=8)
        self.status = ttk.Label(panel, text="Inicializando...", wraplength=250, 
                               font=("Segoe UI", 9), foreground="#555")
        self.status.grid(row=32, column=0, columnspan=2, sticky="w")

        # Layout
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # Cámara
        self.cap = None
        self.current_frame = None

        # MQTT
        self._setup_mqtt(host="10.25.90.33", port=1883,
                         user=None, password=None,
                         topic="datos/score",
                         incoming_topic="camara/estadoTurno")

        self.detect_and_fill()
        self.open_camera()
        self.update_loop()

    # ---- MQTT ----
    def _setup_mqtt(self, host="10.25.90.33", port=1883,
                    user=None, password=None, topic="datos/score",
                    incoming_topic="camara/estadoTurno"):
        self.mqtt_topic = topic
        self.mqtt_in_topic = incoming_topic
        try:
            self.mqtt = mqtt.Client(protocol=mqtt.MQTTv311)
        except TypeError:
            self.mqtt = mqtt.Client()
        if user and password:
            self.mqtt.username_pw_set(user, password)
        try:
            self.mqtt.on_message = self._on_mqtt_message
            self.mqtt.connect(host, port, keepalive=60)
            self.mqtt.loop_start()
            try:
                self.mqtt.subscribe(self.mqtt_in_topic)
            except Exception:
                pass
            self.status.configure(text=f"✓ MQTT conectado ({host}:{port})")
        except Exception as e:
            self.mqtt = None
            self.status.configure(text=f"⚠ MQTT no disponible: {e}")

    def _publish_score(self, score_value, ts=None, mode=None):
        if not hasattr(self, "mqtt") or self.mqtt is None:
            return
        payload_str = f"{score_value:.3f}"
        try:
            self.mqtt.publish(self.mqtt_topic, payload_str, qos=0, retain=False)
            print(f"[MQTT] Publicado score: {payload_str}")
        except Exception as e:
            print(f"[MQTT] Error: {e}")

    def _on_mqtt_message(self, client, userdata, msg):
        payload = msg.payload
        try:
            val = payload.decode("utf-8").strip()
        except Exception:
            val = ""

        def parse_bool(s):
            if s is None:
                return None
            if isinstance(s, bool):
                return s
            if isinstance(s, (int, float)):
                return bool(s)
            if isinstance(s, bytes):
                try:
                    s = s.decode("utf-8")
                except Exception:
                    return None
            if not isinstance(s, str):
                s = str(s)
            s2 = s.strip().lower()
            if s2 in ("true", "1", "on", "si", "yes"):
                return True
            if s2 in ("false", "0", "off", "no"):
                return False
            try:
                j = json.loads(s)
                if isinstance(j, bool):
                    return j
                if isinstance(j, dict):
                    for k in ("estado","turno","value","on","estadoTurno"):
                        if k in j:
                            v = j[k]
                            if isinstance(v, bool):
                                return v
                            if isinstance(v, (int,float)):
                                return bool(v)
                            if isinstance(v, str):
                                return parse_bool(v)
            except Exception:
                pass
            return None

        b = parse_bool(val)
        if b is None:
            b = parse_bool(payload)
        self.root.after(0, lambda: self._handle_incoming_turno(b, msg.topic))

    def _handle_incoming_turno(self, val, topic=None):
        if val is None:
            self.status.configure(text=f"⚠ Payload no válido en {topic}")
            return
        if val:
            self.status.configure(text="[MQTT] Turno=true → Foto 1")
            self.take_photo1()
        else:
            self.status.configure(text="[MQTT] Turno=false → Comparando")
            self.take_photo2_compare()

    # --- Detección cámaras ---
    def detect_and_fill(self, max_index: int = 10):
        found = []
        for i in range(0, max_index + 1):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            ok = cap.isOpened()
            ret = False
            if ok:
                ret, _ = cap.read()
            cap.release()
            if ok and ret:
                found.append(str(i))
        if not found:
            found = ["0"]
        self.combo_cam["values"] = found
        if self.var_cam_idx.get() not in found:
            self.var_cam_idx.set(found[0])
        self.status.configure(text=f"📹 Cámaras: {', '.join(found)}")

    # --- ROI ---
    def define_roi(self):
        if self.current_frame is None:
            self.status.configure(text="⚠ No hay frame")
            return
        
        clone = self.current_frame.copy()
        cv2.putText(clone, "Selecciona area - ENTER:OK, C:Cancelar", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        self.roi = cv2.selectROI("Definir Area", clone, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow("Definir Area")
        
        if self.roi[2] > 0 and self.roi[3] > 0:
            self.status.configure(text=f"✓ ROI: {self.roi[2]}x{self.roi[3]}px")
            self.var_use_roi.set(True)
        else:
            self.roi = None
            self.status.configure(text="✗ ROI cancelado")
            self.var_use_roi.set(False)

    def _apply_roi(self, img):
        if not self.var_use_roi.get() or self.roi is None:
            return img
        x, y, w, h = self.roi
        if w > 0 and h > 0:
            return img[y:y+h, x:x+w].copy()
        return img

    # --- Cámara ---
    def open_camera(self):
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass

        try:
            cam_index = int(self.var_cam_idx.get())
        except Exception:
            cam_index = 0

        try:
            width, height = [int(x) for x in self.var_res.get().split("x")]
        except Exception:
            width, height = 1280, 720

        self.cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(cam_index)

        if not self.cap.isOpened():
            self.status.configure(text=f"✗ No se pudo abrir cámara {cam_index}")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.status.configure(text=f"✓ Cámara {cam_index} ({width}x{height})")

    def update_loop(self):
        if self.cap is not None and self.cap.isOpened():
            ok, frame = self.cap.read()
            if ok:
                self.current_frame = frame
                
                frame_disp = frame.copy()
                if self.roi is not None and self.roi[2] > 0:
                    x, y, w, h = self.roi
                    cv2.rectangle(frame_disp, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame_disp, "ROI", (x, y-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                h, w = frame_disp.shape[:2]
                scale = min(self.preview_w / float(w), 1.0)
                frame_disp = cv2.resize(frame_disp, (int(w*scale), int(h*scale))) \
                    if scale < 1.0 else frame_disp
                rgb = cv2.cvtColor(frame_disp, cv2.COLOR_BGR2RGB)
                imgtk = ImageTk.PhotoImage(Image.fromarray(rgb))
                self.preview_label.imgtk = imgtk
                self.preview_label.configure(image=imgtk)
        self.root.after(20, self.update_loop)

    # --- Acciones ---
    def take_photo1(self):
        if self.current_frame is None:
            self.status.configure(text="⚠ No hay frame")
            return
        
        self.photo1 = self._apply_roi(self.current_frame.copy())
        
        # CONTAR HERRAMIENTAS
        blur_slider = int(round(self.var_blur.get()))
        blur = ensure_odd(blur_slider) if blur_slider > 0 else 0
        morph = int(round(self.var_morph.get()))
        thresh = int(round(self.var_thresh.get()))
        min_area = int(self.var_min_area.get())
        
        self.tools_in_reference, tool_areas = count_tools_in_image(
            self.photo1, blur=blur, thresh=thresh, morph=morph, min_area=min_area
        )
        
        self.lbl_tools_ref.configure(
            text=f"🔧 Herramientas detectadas: {self.tools_in_reference}"
        )
        
        self.status.configure(
            text=f"✓ Foto 1 capturada | {self.tools_in_reference} herramientas detectadas"
        )
        self.last_result = None
        self.save_btn.configure(state="disabled")

    def _maybe_align(self, f1, f2):
        if not self.var_align.get():
            return f2
        aligned, ok = align_ecc(f1, f2)
        return aligned

    def take_photo2_compare(self):
        if self.photo1 is None:
            self.status.configure(text="⚠ Primero toma Foto 1")
            return
        if self.current_frame is None:
            self.status.configure(text="⚠ No hay frame")
            return

        photo2_raw = self._apply_roi(self.current_frame.copy())
        photo2 = self._maybe_align(self.photo1, photo2_raw)

        blur_slider = int(round(self.var_blur.get()))
        blur = ensure_odd(blur_slider) if blur_slider > 0 else 0
        morph = int(round(self.var_morph.get()))
        thresh = int(round(self.var_thresh.get()))
        mode = self.var_mode.get()

        # Comparación base
        if mode == "AbsDiff":
            mask, base_view, changed, pct = compare_absdiff(
                self.photo1, photo2, blur=blur, thresh=thresh, morph=morph
            )
            mask_or_map = mask
        elif mode == "SSIM (mapa)":
            mask, base_view, changed, pct = compare_ssim(
                self.photo1, photo2, blur=blur, thresh=thresh, morph=morph
            )
            mask_or_map = base_view
        else:
            mask, base_view, changed, pct = compare_edges(
                self.photo1, photo2, blur=blur, thresh=thresh, morph=morph
            )
            mask_or_map = mask

        diff_view = base_view
        extra_txt = ""
        score_final = 0.0

        if self.var_boxes.get():
            # MODO INTELIGENTE
            overlay, add_cnt, rem_cnt, total_area, score_intelligent, tools_photo2 = \
                detect_added_removed_smart(
                    self.photo1, photo2,
                    blur=blur, thresh=thresh,
                    morph=morph, min_area=int(self.var_min_area.get()),
                    tools_in_reference=self.tools_in_reference
                )
            diff_view = overlay
            score_final = score_intelligent
            
            tools_missing = max(0, self.tools_in_reference - tools_photo2) if self.tools_in_reference else 0
            
            extra_txt = (
                f"🔧 Herramientas: Ref={self.tools_in_reference} | Actual={tools_photo2} | Faltan={tools_missing}\n"
                f"📊 Añadidos: {add_cnt} | Removidos: {rem_cnt}\n"
                f"💡 Score: {score_intelligent:.1f}% (70% conteo + 30% área×12)"
            )
        else:
            # Modo simple
            total_pixels = mask.size
            pct_area = (changed / float(total_pixels)) * 100.0
            score_final = min(pct_area * 12.0, 100.0)
            extra_txt = f"📊 Score (área ×12): {score_final:.1f}%"

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.last_result = (
            mask, diff_view, changed, score_final, ts,
            self.photo1.copy(), photo2.copy()
        )
        
        # Interpretación
        if score_final <= 15.0:
            interpretation = "✅ TODO OK"
        elif score_final <= 35.0:
            interpretation = "⚠️ ADVERTENCIA"
        elif score_final <= 60.0:
            interpretation = "⚠️ ALERTA - Falta herramienta"
        else:
            interpretation = "❌ CRÍTICO - Faltan varias"
        
        self.status.configure(text=f"[{mode}] {interpretation} | Score: {score_final:.1f}%")
        self.save_btn.configure(state="normal")

        self._publish_score(score_final, ts=ts, mode=mode)

        if self.comp_win is None or not self.comp_win.winfo_exists():
            self.comp_win = ComparisonWindow(self.root, max_w=520)
        self.comp_win.update_images(
            self.photo1, photo2, mask_or_map, diff_view,
            score_final, changed, extra_txt=extra_txt
        )
        self.comp_win.lift()

    def save_results(self):
        if self.last_result is None:
            return
        mask, diff_view, changed, score, ts, f1, f2 = self.last_result
        out = self.outdir
        cv2.imwrite(str(out / f"{ts}_photo1_ref.png"), f1)
        cv2.imwrite(str(out / f"{ts}_photo2_actual.png"), f2)
        cv2.imwrite(str(out / f"{ts}_mask.png"), mask)
        cv2.imwrite(str(out / f"{ts}_diff.png"), diff_view)
        meta = {
            "timestamp": ts,
            "score_intelligent": float(f"{score:.6f}"),
            "tools_reference": self.tools_in_reference,
            "changed_pixels": int(changed),
            "modo": self.var_mode.get(),
            "config": {
                "umbral": int(self.var_thresh.get()),
                "blur": int(self.var_blur.get()),
                "morph": int(self.var_morph.get()),
                "min_area": int(self.var_min_area.get())
            }
        }
        (out / f"{ts}_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        self.status.configure(text=f"💾 Guardado en: {out.resolve()}")

    def reset(self):
        self.photo1 = None
        self.last_result = None
        self.tools_in_reference = None
        self.lbl_tools_ref.configure(text="Herramientas en referencia: --")
        self.save_btn.configure(state="disabled")
        self.status.configure(text="🔄 Listo")

    def on_close(self):
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        try:
            if hasattr(self, "mqtt") and self.mqtt is not None:
                self.mqtt.loop_stop()
                self.mqtt.disconnect()
        except Exception:
            pass
        cv2.destroyAllWindows()
        self.root.destroy()

# ---------- Run ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = CamDiffApp(root)
    root.mainloop()