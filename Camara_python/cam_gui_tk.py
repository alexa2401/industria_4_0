# -*- coding: utf-8 -*-
"""
CamDiff GUI (Tkinter) - Python 3.13
Comparaciones: AbsDiff, SSIM (mapa), Bordes (Canny)
Alineado opcional (ECC). Tarjeta coloreada por % de cambio.

Requisitos: pillow, opencv-python, numpy
"""

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# ---------- Utilidades ----------
def ensure_odd(x: int) -> int:
    return x if x % 2 == 1 else x + 1

def color_for_pct(pct: float) -> str:
    if pct <= 1.0:
        return "#2ecc71"   # verde
    elif pct <= 10.0:
        return "#f1c40f"   # amarillo
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

# --- SSIM en NumPy (grayscale) ---
def ssim_map(gray1, gray2, ksize=11, sigma=1.5):
    # ventana gaussiana
    k = cv2.getGaussianKernel(ksize, sigma)
    w = k @ k.T
    mu1 = cv2.filter2D(gray1, -1, w)
    mu2 = cv2.filter2D(gray2, -1, w)
    mu1_sq, mu2_sq, mu1_mu2 = mu1*mu1, mu2*mu2, mu1*mu2
    sigma1_sq = cv2.filter2D(gray1*gray1, -1, w) - mu1_sq
    sigma2_sq = cv2.filter2D(gray2*gray2, -1, w) - mu2_sq
    sigma12   = cv2.filter2D(gray1*gray2, -1, w) - mu1_mu2
    # constantes (dinámica 255)
    C1, C2 = (0.01*255)**2, (0.03*255)**2
    num = (2*mu1_mu2 + C1)*(2*sigma12 + C2)
    den = (mu1_sq + mu2_sq + C1)*(sigma1_sq + sigma2_sq + C2)
    ssim = num / (den + 1e-12)
    ssim = np.clip(ssim, 0, 1)
    return ssim

# --- Alineado ECC (opcional) ---
def align_ecc(img1, img2):
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    g1 = cv2.GaussianBlur(g1, (5,5), 0)
    g2 = cv2.GaussianBlur(g2, (5,5), 0)
    warp = np.eye(2, 3, dtype=np.float32)   # afin
    try:
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-5)
        cc, warp = cv2.findTransformECC(g1, g2, warp, cv2.MOTION_EUCLIDEAN, criteria)
        aligned = cv2.warpAffine(img2, warp, (img2.shape[1], img2.shape[0]), flags=cv2.INTER_LINEAR+cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
        return aligned, True
    except Exception:
        return img2, False

# --- Comparaciones ---
def compare_absdiff(img1, img2, blur=5, thresh=25, morph=3):
    if img1.shape != img2.shape: raise ValueError("Tamaños distintos.")
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
    diff_col = cv2.cvtColor(diff, cv2.COLOR_GRAY2BGR); diff_col[mask>0] = [0,0,255]
    changed = int(np.sum(mask>0)); pct = (changed / mask.size) * 100.0
    return mask, diff_col, changed, pct

def compare_ssim(img1, img2, blur=3, thresh=25, morph=3):
    if img1.shape != img2.shape:
        raise ValueError("Tamaños distintos.")

    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    if blur and blur > 1:
        k = blur if blur % 2 else blur + 1
        g1 = cv2.GaussianBlur(g1, (k, k), 0)
        g2 = cv2.GaussianBlur(g2, (k, k), 0)

    # ----- SSIM map en [0..1] -----
    ssim = ssim_map(g1.astype(np.float32), g2.astype(np.float32))
    change = 1.0 - ssim  # 0 = iguales, 1 = muy diferentes

    # Umbral (re-usa slider de 0..255)
    thr = np.clip(thresh / 255.0, 0.0, 1.0)
    mask = (change >= thr).astype(np.uint8) * 255  # uint8 para OpenCV

    if morph and morph > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, 1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, 1)

    # Heatmap de cambio (BGR uint8)
    heat = (change * 255).astype(np.uint8)
    heat_col = cv2.applyColorMap(heat, cv2.COLORMAP_JET)

    # Mezcla con rojo SOLO en la zona enmascarada:
    red_img = np.zeros_like(heat_col, dtype=np.uint8)
    red_img[:] = (0, 0, 255)
    blended = cv2.addWeighted(heat_col, 0.6, red_img, 0.4, 0)
    heat_col[mask > 0] = blended[mask > 0]

    changed = int(np.sum(mask > 0))
    pct = float(change.mean() * 100.0)  # aprox = (1 - SSIM medio)*100

    return mask, heat_col, changed, pct


def compare_edges(img1, img2, blur=3, thresh=50, morph=3):
    if img1.shape != img2.shape: raise ValueError("Tamaños distintos.")
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
    mask = (diff_edges > 0).astype(np.uint8)*255
    diff_col = cv2.cvtColor(g2, cv2.COLOR_GRAY2BGR); diff_col[mask>0] = [0,0,255]
    changed = int(np.sum(mask>0)); pct = (changed / mask.size) * 100.0
    return mask, diff_col, changed, pct

# ---------- Ventana de comparación (tarjeta coloreada) ----------
class ComparisonWindow(tk.Toplevel):
    def __init__(self, master, max_w=520):
        super().__init__(master)
        self.title("Comparación")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.max_w = max_w

        self.card = tk.Frame(self, bd=0, highlightthickness=0, bg="#eeeeee")
        self.card.pack(padx=10, pady=10, fill="both", expand=True)

        self.inner = tk.Frame(self.card, bg=self.card["bg"])
        self.inner.pack(padx=12, pady=12)

        for col, txt in enumerate(("Foto 1", "Mask/Mapa")):
            tk.Label(self.inner, text=txt, font=("Segoe UI", 10, "bold"), bg=self.inner["bg"]).grid(row=0, column=col, sticky="s")
        for col, txt in enumerate(("Foto 2", "Diff/Resalte")):
            tk.Label(self.inner, text=txt, font=("Segoe UI", 10, "bold"), bg=self.inner["bg"]).grid(row=2, column=col, sticky="s")

        self.lbl_f1 = tk.Label(self.inner, bg=self.inner["bg"]); self.lbl_f1.grid(row=1, column=0, padx=6, pady=4)
        self.lbl_mk = tk.Label(self.inner, bg=self.inner["bg"]); self.lbl_mk.grid(row=1, column=1, padx=6, pady=4)
        self.lbl_f2 = tk.Label(self.inner, bg=self.inner["bg"]); self.lbl_f2.grid(row=3, column=0, padx=6, pady=4)
        self.lbl_df = tk.Label(self.inner, bg=self.inner["bg"]); self.lbl_df.grid(row=3, column=1, padx=6, pady=4)

        self._img_refs = []

        self.txt = tk.Label(self, text="—", anchor="w")
        self.txt.pack(fill="x", padx=10, pady=(0,10))

        tk.Button(self, text="Cerrar", command=self.on_close).pack(pady=(0,10))

    def _apply_card_color(self, color: str):
        self.card.configure(bg=color)
        self.inner.configure(bg=color)
        for w in (self.lbl_f1, self.lbl_mk, self.lbl_f2, self.lbl_df):
            w.configure(bg=color)
        for child in self.inner.grid_slaves():
            if isinstance(child, tk.Label) and child not in (self.lbl_f1,self.lbl_mk,self.lbl_f2,self.lbl_df):
                child.configure(bg=color)

    def update_images(self, photo1_bgr, photo2_bgr, mask_gray_or_map, diff_bgr, pct, changed):
        self._img_refs.clear()
        self._apply_card_color(color_for_pct(pct))

        im_f1 = bgr_to_tk(photo1_bgr, self.max_w); self._img_refs.append(im_f1); self.lbl_f1.configure(image=im_f1)
        # mask_gray_or_map puede ser GRAY o BGR (SSIM heatmap). Convertimos si es necesario.
        if len(mask_gray_or_map.shape) == 2:
            im_mk = gray_to_tk(mask_gray_or_map,  self.max_w)
        else:
            im_mk = bgr_to_tk(mask_gray_or_map,   self.max_w)
        self._img_refs.append(im_mk); self.lbl_mk.configure(image=im_mk)

        im_f2 = bgr_to_tk(photo2_bgr,  self.max_w); self._img_refs.append(im_f2); self.lbl_f2.configure(image=im_f2)
        im_df = bgr_to_tk(diff_bgr,    self.max_w); self._img_refs.append(im_df); self.lbl_df.configure(image=im_df)

        self.txt.configure(text=f"Cambio: {pct:.3f}%  |  Píxeles: {changed}")

    def on_close(self):
        self.destroy()

# ---------- App principal ----------
class CamDiffApp:
    def __init__(self, root):
        self.root = root
        root.title("CamDiff GUI (Tkinter)")
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.preview_w = 900
        self.photo1 = None
        self.last_result = None
        self.outdir = Path("outputs"); self.outdir.mkdir(parents=True, exist_ok=True)
        self.comp_win = None

        # Vista previa
        self.preview_label = ttk.Label(root)
        self.preview_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Panel derecho
        panel = ttk.Frame(root); panel.grid(row=0, column=1, padx=10, pady=10, sticky="ns")
        ttk.Label(panel, text="Controles", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0,8))
        ttk.Button(panel, text="Tomar Foto 1", command=self.take_photo1).grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(panel, text="Tomar Foto 2 y comparar", command=self.take_photo2_compare).grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(panel, text="Reiniciar", command=self.reset).grid(row=3, column=0, sticky="ew", pady=2)
        self.save_btn = ttk.Button(panel, text="Guardar resultados", command=self.save_results, state="disabled")
        self.save_btn.grid(row=3, column=1, sticky="ew", pady=2)

        # Modo + opciones
        ttk.Label(panel, text="Modo de comparación").grid(row=4, column=0, columnspan=2, sticky="w", pady=(8,0))
        self.var_mode = tk.StringVar(value="AbsDiff")
        ttk.Combobox(panel, values=["AbsDiff","SSIM (mapa)","Bordes (Canny)"], textvariable=self.var_mode, state="readonly").grid(row=5, column=0, columnspan=2, sticky="ew", pady=2)

        self.var_align = tk.BooleanVar(value=True)
        ttk.Checkbutton(panel, text="Alinear antes (ECC)", variable=self.var_align).grid(row=6, column=0, columnspan=2, sticky="w")

        ttk.Label(panel, text="Umbral (thresh)").grid(row=7, column=0, columnspan=2, sticky="w", pady=(8,0))
        self.var_thresh = tk.IntVar(value=25)
        ttk.Scale(panel, from_=0, to=255, orient="horizontal", variable=self.var_thresh).grid(row=8, column=0, columnspan=2, sticky="ew", pady=2)

        ttk.Label(panel, text="Blur (impar)").grid(row=9, column=0, columnspan=2, sticky="w")
        self.var_blur = tk.IntVar(value=5)
        ttk.Scale(panel, from_=0, to=21, orient="horizontal", variable=self.var_blur).grid(row=10, column=0, columnspan=2, sticky="ew", pady=2)

        ttk.Label(panel, text="Morph (px)").grid(row=11, column=0, columnspan=2, sticky="w")
        self.var_morph = tk.IntVar(value=3)
        ttk.Scale(panel, from_=0, to=21, orient="horizontal", variable=self.var_morph).grid(row=12, column=0, columnspan=2, sticky="ew", pady=2)

        ttk.Label(panel, text="Cámara (índice)").grid(row=13, column=0, sticky="w", pady=(8,0))
        self.var_cam = tk.StringVar(value="0")
        ttk.Entry(panel, textvariable=self.var_cam, width=6).grid(row=13, column=1, sticky="e", pady=(8,0))

        ttk.Label(panel, text="Resolución").grid(row=14, column=0, sticky="w")
        self.var_res = tk.StringVar(value="1280x720")
        ttk.Combobox(panel, values=["640x480","1280x720","1920x1080"], textvariable=self.var_res, state="readonly", width=12).grid(row=14, column=1, sticky="e")

        self.status = ttk.Label(panel, text="Inicializando...")
        self.status.grid(row=15, column=0, columnspan=2, sticky="w", pady=(8,0))

        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # Cámara
        self.cap = None
        self.current_frame = None
        self.open_camera()
        self.update_loop()

    # --- Cámara y preview ---
    def open_camera(self):
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass

        try:
            cam_index = int(self.var_cam.get())
        except Exception:
            cam_index = 0
            self.var_cam.set("0")

        try:
            width, height = [int(x) for x in self.var_res.get().split("x")]
        except Exception:
            width, height = 1280, 720
            self.var_res.set("1280x720")

        self.cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(cam_index)

        if not self.cap.isOpened():
            self.status.configure(text="No se pudo abrir la cámara. ¿Índice correcto? ¿Webcam libre?")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.status.configure(text=f"Cámara abierta (idx {cam_index}) {width}x{height}")

    def update_loop(self):
        if self.cap is not None and self.cap.isOpened():
            ok, frame = self.cap.read()
            if ok:
                self.current_frame = frame
                h, w = frame.shape[:2]
                scale = min(self.preview_w / float(w), 1.0)
                frame_disp = cv2.resize(frame, (int(w*scale), int(h*scale))) if scale < 1.0 else frame
                rgb = cv2.cvtColor(frame_disp, cv2.COLOR_BGR2RGB)
                imgtk = ImageTk.PhotoImage(Image.fromarray(rgb))
                self.preview_label.imgtk = imgtk
                self.preview_label.configure(image=imgtk)
            else:
                self.status.configure(text="Sin frame (¿otra app usa la cámara?)")
        self.root.after(20, self.update_loop)

    # --- Acciones ---
    def take_photo1(self):
        if self.current_frame is None: return
        self.photo1 = self.current_frame.copy()
        self.status.configure(text="Foto 1 capturada.")
        self.last_result = None
        self.save_btn.configure(state="disabled")

    def _maybe_align(self, f1, f2):
        if not self.var_align.get():
            return f2
        aligned, ok = align_ecc(f1, f2)
        if ok:
            self.status.configure(text="Alineado ECC aplicado.")
        else:
            self.status.configure(text="No se pudo alinear (ECC).")
        return aligned

    def take_photo2_compare(self):
        if self.photo1 is None:
            self.status.configure(text="Primero toma la Foto 1.")
            return
        if self.current_frame is None:
            self.status.configure(text="No hay frame para Foto 2.")
            return

        photo2 = self._maybe_align(self.photo1, self.current_frame.copy())

        blur = int(round(self.var_blur.get()))
        blur = ensure_odd(blur) if blur > 0 else 0
        morph = int(round(self.var_morph.get()))
        thresh = int(round(self.var_thresh.get()))
        mode = self.var_mode.get()

        if mode == "AbsDiff":
            mask, view, changed, pct = compare_absdiff(self.photo1, photo2, blur=blur, thresh=thresh, morph=morph)
        elif mode == "SSIM (mapa)":
            mask, view, changed, pct = compare_ssim(self.photo1, photo2, blur=blur, thresh=thresh, morph=morph)
        else:  # "Bordes (Canny)"
            mask, view, changed, pct = compare_edges(self.photo1, photo2, blur=blur, thresh=thresh, morph=morph)

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.last_result = (mask, view, changed, pct, ts, self.photo1.copy(), photo2.copy())
        self.status.configure(text=f"[{mode}] Cambio: {pct:.2f}%  (píxeles {changed})")
        self.save_btn.configure(state="normal")

        if self.comp_win is None or not self.comp_win.winfo_exists():
            self.comp_win = ComparisonWindow(self.root, max_w=520)
        # En SSIM, "mask_gray_or_map" será el heatmap; en los demás la máscara
        mask_or_map = view if mode == "SSIM (mapa)" else mask
        diff_view = view if mode != "SSIM (mapa)" else view
        self.comp_win.update_images(self.photo1, photo2, mask_or_map, diff_view, pct, changed)
        self.comp_win.lift()

    def save_results(self):
        if self.last_result is None: return
        mask, view, changed, pct, ts, f1, f2 = self.last_result
        out = self.outdir
        p1 = out / f"{ts}_photo1.png"
        p2 = out / f"{ts}_photo2.png"
        pm = out / f"{ts}_mask.png"
        pd = out / f"{ts}_diff.png"
        cv2.imwrite(str(p1), f1)
        cv2.imwrite(str(p2), f2)
        # Si el modo fue SSIM, 'mask' es binaria y 'view' es heatmap
        cv2.imwrite(str(pm), mask)
        cv2.imwrite(str(pd), view)
        self.status.configure(text=f"Guardado en: {out.resolve()}")

    def reset(self):
        self.photo1 = None
        self.last_result = None
        self.save_btn.configure(state="disabled")
        self.status.configure(text="Listo para nuevas fotos.")

    def on_close(self):
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        cv2.destroyAllWindows()
        self.root.destroy()

# ---------- Run ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = CamDiffApp(root)
    root.mainloop()
