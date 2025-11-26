# -*- coding: utf-8 -*-
"""
CamDiff GUI (Tkinter) - Python 3.13
Modos: AbsDiff (original), SSIM (mapa), Bordes (Canny)
Alineado opcional (ECC). Tarjeta coloreada por % de cambio.
Selector de cámaras (detectar/seleccionar/conectar).
Nuevo: Resaltado de objetos añadidos (verde) y removidos (azul) en Foto 2.
Publica el score (pct) por MQTT en 'datos/score'.
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
    warp = np.eye(2, 3, dtype=np.float32)   # afin rigido (rot+trasl)
    try:
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-5)
        _, warp = cv2.findTransformECC(g1, g2, warp, cv2.MOTION_EUCLIDEAN, criteria)
        aligned = cv2.warpAffine(img2, warp, (img2.shape[1], img2.shape[0]),
                                 flags=cv2.INTER_LINEAR+cv2.WARP_INVERSE_MAP,
                                 borderMode=cv2.BORDER_REPLICATE)
        return aligned, True
    except Exception:
        return img2, False

# ---------- Comparaciones base ----------
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
    diff_col = cv2.cvtColor(diff, cv2.COLOR_GRAY2BGR)
    diff_col[mask > 0] = [0, 0, 255]
    changed = int(np.sum(mask > 0))
    pct = (changed / mask.size) * 100.0
    return mask, diff_col, changed, pct

def compare_ssim(img1, img2, blur=3, thresh=25, morph=3):
    if img1.shape != img2.shape: raise ValueError("Tamaños distintos.")
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    if blur and blur > 1:
        k = blur if blur % 2 else blur + 1
        g1 = cv2.GaussianBlur(g1, (k, k), 0)
        g2 = cv2.GaussianBlur(g2, (k, k), 0)

    ssim = ssim_map(g1.astype(np.float32), g2.astype(np.float32))
    change = 1.0 - ssim  # 0 igual; 1 muy diferente
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
    pct = float(change.mean() * 100.0)  # ≈ (1-SSIM medio)*100
    return mask, heat_col, changed, pct

def compare_edges(img1, img2, blur=3, thresh=50, morph=3):
    if img1.shape != img2.shape: raise ValueError("Tamaños distintos.")
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    if blur and blur > 1:
        k = blur if blur % 2 else blur + 1
        g1 = cv2.GaussianBlur(g1, (k, k), 0)
        g2 = cv2.GaussianBlur(g2, (k, k), 0)
    # Nota: aquí podrías mapear 'thresh' a low/high de Canny si lo deseas.
    e1 = cv2.Canny(g1, 50, 150)
    e2 = cv2.Canny(g2, 50, 150)
    diff_edges = cv2.bitwise_xor(e1, e2)
    if morph and morph > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        diff_edges = cv2.morphologyEx(diff_edges, cv2.MORPH_CLOSE, kernel, 1)
    mask = (diff_edges > 0).astype(np.uint8) * 255
    diff_col = cv2.cvtColor(g2, cv2.COLOR_GRAY2BGR); diff_col[mask > 0] = [0, 0, 255]
    changed = int(np.sum(mask > 0)); pct = (changed / mask.size) * 100.0
    return mask, diff_col, changed, pct

# ---------- Detección de "Añadido" vs "Removido" ----------
def detect_added_removed(img1, img2, blur=5, thresh=25, morph=3, min_area=150):
    """
    Retorna:
      overlay_bgr: Foto2 con boxes y relleno (verde: añadido, azul: removido)
      added_count, removed_count
    """
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    if blur and blur > 1:
        k = blur if blur % 2 else blur + 1
        g1 = cv2.GaussianBlur(g1, (k,k), 0)
        g2 = cv2.GaussianBlur(g2, (k,k), 0)

    # Diferencias con signo
    pos = cv2.subtract(g2, g1)  # >0 donde Foto2 es más "fuerte" (potencial añadido)
    neg = cv2.subtract(g1, g2)  # >0 donde Foto1 era más "fuerte" (potencial removido)

    _, add_mask = cv2.threshold(pos, thresh, 255, cv2.THRESH_BINARY)
    _, rem_mask = cv2.threshold(neg, thresh, 255, cv2.THRESH_BINARY)

    if morph and morph > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        add_mask = cv2.morphologyEx(add_mask, cv2.MORPH_OPEN, kernel, 1)
        add_mask = cv2.morphologyEx(add_mask, cv2.MORPH_CLOSE, kernel, 1)
        rem_mask = cv2.morphologyEx(rem_mask, cv2.MORPH_OPEN, kernel, 1)
        rem_mask = cv2.morphologyEx(rem_mask, cv2.MORPH_CLOSE, kernel, 1)

    overlay = img2.copy()

    # Relleno semitransparente
    def draw_regions(bin_mask, color_bgr, label):
        count = 0
        contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area:  # filtrar ruido
                continue
            x,y,w,h = cv2.boundingRect(c)
            # caja
            cv2.rectangle(overlay, (x,y), (x+w,y+h), color_bgr, 2)
            # relleno
            roi = overlay[y:y+h, x:x+w]
            tint = np.full_like(roi, color_bgr, dtype=np.uint8)
            cv2.addWeighted(tint, 0.25, roi, 0.75, 0, dst=roi)
            # etiqueta
            cv2.putText(overlay, label, (x, max(0,y-6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_bgr, 2, cv2.LINE_AA)
            count += 1
        return count

    added = draw_regions(add_mask, (0,255,0), "Añadido")
    removed = draw_regions(rem_mask, (255,0,0), "Removido")
    return overlay, added, removed

# ---------- Ventana de comparación ----------
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

    def update_images(self, photo1_bgr, photo2_bgr, mask_gray_or_map, diff_bgr, pct, changed, extra_txt=""):
        self._img_refs.clear()
        self._apply_card_color(color_for_pct(pct))

        im_f1 = bgr_to_tk(photo1_bgr, self.max_w); self._img_refs.append(im_f1); self.lbl_f1.configure(image=im_f1)
        if len(mask_gray_or_map.shape) == 2:
            im_mk = gray_to_tk(mask_gray_or_map,  self.max_w)
        else:
            im_mk = bgr_to_tk(mask_gray_or_map,   self.max_w)
        self._img_refs.append(im_mk); self.lbl_mk.configure(image=im_mk)

        im_f2 = bgr_to_tk(photo2_bgr,  self.max_w); self._img_refs.append(im_f2); self.lbl_f2.configure(image=im_f2)
        im_df = bgr_to_tk(diff_bgr,    self.max_w); self._img_refs.append(im_df); self.lbl_df.configure(image=im_df)

        base = f"Cambio: {pct:.3f}%  |  Píxeles: {changed}"
        self.txt.configure(text= base + (f"   |   {extra_txt}" if extra_txt else ""))

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

        # --- Selector de cámara ---
        ttk.Label(panel, text="Cámara disponible").grid(row=4, column=0, columnspan=2, sticky="w", pady=(8,0))
        self.var_cam_idx = tk.StringVar(value="0")
        self.combo_cam = ttk.Combobox(panel, textvariable=self.var_cam_idx, state="readonly", width=12)
        self.combo_cam.grid(row=5, column=0, columnspan=2, sticky="ew")
        self.combo_cam.bind("<<ComboboxSelected>>", lambda e: self.open_camera())
        ttk.Button(panel, text="Detectar cámaras", command=self.detect_and_fill)\
            .grid(row=6, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(panel, text="Conectar", command=self.open_camera)\
            .grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0,8))

        # --- Modo y opciones ---
        ttk.Label(panel, text="Modo de comparación").grid(row=8, column=0, columnspan=2, sticky="w", pady=(8,0))
        self.var_mode = tk.StringVar(value="AbsDiff")
        ttk.Combobox(panel, values=["AbsDiff","SSIM (mapa)","Bordes (Canny)"],
                     textvariable=self.var_mode, state="readonly").grid(row=9, column=0, columnspan=2, sticky="ew", pady=2)

        self.var_align = tk.BooleanVar(value=True)
        ttk.Checkbutton(panel, text="Alinear antes (ECC)", variable=self.var_align).grid(row=10, column=0, columnspan=2, sticky="w")

        ttk.Label(panel, text="Umbral (thresh)").grid(row=11, column=0, columnspan=2, sticky="w", pady=(8,0))
        self.var_thresh = tk.IntVar(value=25)
        ttk.Scale(panel, from_=0, to=255, orient="horizontal", variable=self.var_thresh).grid(row=12, column=0, columnspan=2, sticky="ew", pady=2)

        ttk.Label(panel, text="Blur (impar)").grid(row=13, column=0, columnspan=2, sticky="w")
        self.var_blur = tk.IntVar(value=5)
        ttk.Scale(panel, from_=0, to=21, orient="horizontal", variable=self.var_blur).grid(row=14, column=0, columnspan=2, sticky="ew", pady=2)

        ttk.Label(panel, text="Morph (px)").grid(row=15, column=0, columnspan=2, sticky="w")
        self.var_morph = tk.IntVar(value=3)
        ttk.Scale(panel, from_=0, to=21, orient="horizontal", variable=self.var_morph).grid(row=16, column=0, columnspan=2, sticky="ew", pady=2)

        # --- Resaltado de objetos (nuevo) ---
        self.var_boxes = tk.BooleanVar(value=True)
        ttk.Checkbutton(panel, text="Resaltar objetos (cajas)", variable=self.var_boxes).grid(row=17, column=0, columnspan=2, sticky="w")

        ttk.Label(panel, text="Área mínima (px)").grid(row=18, column=0, columnspan=2, sticky="w", pady=(8,0))
        self.var_min_area = tk.IntVar(value=150)
        ttk.Scale(panel, from_=0, to=5000, orient="horizontal", variable=self.var_min_area).grid(row=19, column=0, columnspan=2, sticky="ew", pady=2)

        # Resolución
        ttk.Label(panel, text="Resolución").grid(row=20, column=0, sticky="w", pady=(8,0))
        self.var_res = tk.StringVar(value="1280x720")
        ttk.Combobox(panel, values=["640x480","1280x720","1920x1080"],
                     textvariable=self.var_res, state="readonly", width=12).grid(row=20, column=1, sticky="e")

        self.status = ttk.Label(panel, text="Inicializando...")
        self.status.grid(row=21, column=0, columnspan=2, sticky="w", pady=(8,0))

        # Layout flexible
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # Cámara
        self.cap = None
        self.current_frame = None

        # MQTT: ajusta host/puerto/credenciales según tu broker
        self._setup_mqtt(host="10.25.90.33", port=1883, user=None, password=None, topic="datos/score", incoming_topic="camara/estadoTurno")

        self.detect_and_fill()
        self.open_camera()
        self.update_loop()

    # ---- MQTT helpers ----
    def _setup_mqtt(self, host="10.25.90.33", port=1883, user=None, password=None, topic="datos/score", incoming_topic="camara/estadoTurno"):
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
            # subscribe to incoming topic for trigger messages
            try:
                self.mqtt.subscribe(self.mqtt_in_topic)
            except Exception:
                pass
            self.status.configure(text=f"MQTT conectado a {host}:{port} (topic out: {topic}, in: {incoming_topic})")
        except Exception as e:
            self.mqtt = None
            self.status.configure(text=f"MQTT no disponible: {e}")

    def _publish_score(self, score_value, ts=None, mode=None):
        if not hasattr(self, "mqtt") or self.mqtt is None:
            return
        # Versión simple: solo el número (string)
        payload_str = f"{score_value:.3f}"
        try:
            self.mqtt.publish(self.mqtt_topic, payload_str, qos=0, retain=False)
        except Exception:
            pass

        # OPCIONAL: versión JSON (descomenta si prefieres JSON)
        # payload = {"ts": ts, "mode": mode, "score": float(f"{score_value:.6f}")}
        # try:
        #     self.mqtt.publish(self.mqtt_topic, json.dumps(payload), qos=0, retain=False)
        # except Exception:
        #     pass

    def _on_mqtt_message(self, client, userdata, msg):
        # se ejecuta en el hilo del cliente MQTT -> despachar al hilo de la GUI
        payload = msg.payload
        try:
            val = payload.decode("utf-8").strip()
        except Exception:
            val = ""
        # parseo robusto a booleano
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
                    s = None
            if not isinstance(s, str):
                s = str(s)
            s2 = s.strip().lower()
            if s2 in ("true", "1", "on", "si", "yes"):
                return True
            if s2 in ("false", "0", "off", "no"):
                return False
            # try JSON
            try:
                j = json.loads(s)
                if isinstance(j, bool):
                    return j
                if isinstance(j, dict):
                    for k in ("estado", "turno", "value", "on", "estadoTurno"):
                        if k in j:
                            v = j[k]
                            if isinstance(v, bool):
                                return v
                            if isinstance(v, (int, float)):
                                return bool(v)
                            if isinstance(v, str):
                                return parse_bool(v)
                # array maybe: take first boolean-ish element
                if isinstance(j, (list, tuple)) and j:
                    return parse_bool(j[0])
            except Exception:
                pass
            return None

        b = parse_bool(val)
        if b is None:
            # try last resort if payload bytes looked like b'true' etc.
            b = parse_bool(payload)
        # schedule action in main thread
        self.root.after(0, lambda: self._handle_incoming_turno(b, msg.topic))

    def _handle_incoming_turno(self, val, topic=None):
        if val is None:
            # ignore unparseable messages but set status for debug
            self.status.configure(text=f"Recibido payload no válido en {topic}")
            return
        if val:
            # equivalent to pressing "Tomar Foto 1"
            self.status.configure(text=f"Recibido TURN: true -> Tomando Foto 1")
            self.take_photo1()
        else:
            # equivalent to pressing "Tomar Foto 2"
            self.status.configure(text=f"Recibido TURN: false -> Tomando Foto 2 y comparando")
            self.take_photo2_compare()

    # --- Detección de cámaras (0..max_index) ---
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
            found = ["0"]  # fallback
        self.combo_cam["values"] = found
        if self.var_cam_idx.get() not in found:
            self.var_cam_idx.set(found[0])
        self.status.configure(text=f"Cámaras: {', '.join(found)}")

    # --- Cámara y preview ---
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
            self.var_cam_idx.set("0")

        try:
            width, height = [int(x) for x in self.var_res.get().split("x")]
        except Exception:
            width, height = 1280, 720
            self.var_res.set("1280x720")

        self.cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(cam_index)

        if not self.cap.isOpened():
            self.status.configure(text=f"No se pudo abrir la cámara índice {cam_index}. ¿Está libre?")
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

        blur = int(round(self.var_blur.get())); blur = ensure_odd(blur) if blur > 0 else 0
        morph = int(round(self.var_morph.get()))
        thresh = int(round(self.var_thresh.get()))
        mode = self.var_mode.get()

        if mode == "AbsDiff":
            mask, base_view, changed, pct = compare_absdiff(self.photo1, photo2, blur=blur, thresh=thresh, morph=morph)
            mask_or_map = mask
        elif mode == "SSIM (mapa)":
            mask, base_view, changed, pct = compare_ssim(self.photo1, photo2, blur=blur, thresh=thresh, morph=morph)
            mask_or_map = base_view  # en la columna Mask/Mapa se muestra el heatmap
        else:  # Canny
            mask, base_view, changed, pct = compare_edges(self.photo1, photo2, blur=blur, thresh=thresh, morph=morph)
            mask_or_map = mask

        # --- Resaltado de añadidos/removidos sobre Foto 2 ---
        diff_view = base_view
        extra_txt = ""
        if self.var_boxes.get():
            overlay, add_cnt, rem_cnt = detect_added_removed(self.photo1, photo2,
                                                             blur=blur, thresh=thresh,
                                                             morph=morph, min_area=int(self.var_min_area.get()))
            diff_view = overlay
            extra_txt = f"Añadidos: {add_cnt} | Removidos: {rem_cnt}"

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.last_result = (mask, diff_view, changed, pct, ts, self.photo1.copy(), photo2.copy())
        self.status.configure(text=f"[{mode}] Cambio: {pct:.2f}% (píxeles {changed})")
        self.save_btn.configure(state="normal")

        # Publicar score por MQTT (tópico 'datos/score')
        self._publish_score(pct, ts=ts, mode=mode)
        print("Publicado score MQTT:", pct)

        if self.comp_win is None or not self.comp_win.winfo_exists():
            self.comp_win = ComparisonWindow(self.root, max_w=520)
        self.comp_win.update_images(self.photo1, photo2, mask_or_map, diff_view, pct, changed, extra_txt=extra_txt)
        self.comp_win.lift()

    def save_results(self):
        if self.last_result is None: return
        mask, diff_view, changed, pct, ts, f1, f2 = self.last_result
        out = self.outdir
        cv2.imwrite(str(out / f"{ts}_photo1.png"), f1)
        cv2.imwrite(str(out / f"{ts}_photo2.png"), f2)
        cv2.imwrite(str(out / f"{ts}_mask.png"),   mask)
        cv2.imwrite(str(out / f"{ts}_diff.png"),   diff_view)
        # (Opcional) guardar metadatos
        meta = {
            "timestamp": ts,
            "pct": float(f"{pct:.6f}"),
            "changed_pixels": int(changed)
        }
        (out / f"{ts}_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
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
