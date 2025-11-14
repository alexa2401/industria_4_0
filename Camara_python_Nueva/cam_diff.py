#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cam_diff.py - Un solo archivo.
Toma dos fotos con la webcam en Windows y compara cambios.

Uso rápido (PowerShell o CMD):
    python cam_diff.py --dshow --width 1280 --height 720 --thresh 25 --blur 5 --morph 3
Teclas:
    ESPACIO = capturar (Foto1 y luego Foto2)
    Q       = salir

Modo automático (sin teclas):
    python cam_diff.py --dshow --auto --delay 3

Requisitos:
    - Python 3.9+ en Windows (con "Add Python to PATH")
    - Webcam
    - Internet para instalar dependencias si faltan (opencv-python, numpy)
"""

import sys, subprocess, time, argparse
from pathlib import Path
from datetime import datetime

# --- Dependencias con auto-instalar ------------------------------------------------------------
def ensure_deps():
    pkgs = ("cv2", "numpy")
    missing = []
    for m in pkgs:
        try:
            __import__(m)
        except Exception:
            missing.append(m)
    if not missing:
        return

    print("[INFO] Faltan dependencias:", missing)
    # Mapa módulo->paquete pip
    to_pip = {"cv2": "opencv-python", "numpy": "numpy"}
    pip_pkgs = [to_pip[m] for m in missing]
    print("[INFO] Intentando instalar automáticamente con pip:", pip_pkgs)
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", *pip_pkgs])
    except Exception as e:
        print("\n[ERROR] No se pudieron instalar automáticamente:", e)
        print("Instala manualmente y vuelve a ejecutar:")
        print("    pip install opencv-python numpy\n")
        sys.exit(1)

ensure_deps()
import cv2
import numpy as np
# -----------------------------------------------------------------------------------------------

def put_text(img, text, y=30):
    """Texto con contorno para que se lea mejor."""
    cv2.putText(img, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)

def take_frame(cap, warmup=0.25):
    """Lee un frame estable tras un pequeño warmup."""
    time.sleep(warmup)
    ok, frame = cap.read()
    if not ok or frame is None:
        raise RuntimeError("No se pudo leer la cámara. Verifica índice y permisos.")
    return frame

def compare_frames(img1, img2, blur=5, thresh=25, morph=3):
    """
    Devuelve: (mask_binaria, diff_color, changed_pixels, percentage)
    - gris -> blur -> absdiff -> threshold -> morfología (open/close).
    """
    if img1.shape != img2.shape:
        raise ValueError("Las imágenes deben tener el mismo tamaño.")
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
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    diff_col = cv2.cvtColor(diff, cv2.COLOR_GRAY2BGR)
    diff_col[mask > 0] = [0, 0, 255]  # rojo = cambio

    changed = int(np.sum(mask > 0))
    total = mask.size
    pct = (changed / total) * 100.0
    return mask, diff_col, changed, pct

def run(args):
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    backend = cv2.CAP_DSHOW if args.dshow else 0
    cap = cv2.VideoCapture(args.camera, backend)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.camera)  # reintento sin forzar backend
        if not cap.isOpened():
            raise RuntimeError("No se pudo abrir la cámara. Prueba con --camera 1 o --dshow.")

    # pedir MJPG para mejorar compatibilidad y FPS en Windows
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    ts_prefix = datetime.now().strftime("%Y%m%d-%H%M%S")
    win = "CamDiff - Vista previa"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    photo1 = None
    photo2 = None

    print("[Instrucciones]")
    if args.auto:
        print(f" - Modo automático activo: tomará Foto 1 ahora y Foto 2 en {args.delay} s.")
    else:
        print(" - Presiona ESPACIO para tomar la Foto 1.")
        print(" - Presiona ESPACIO nuevamente para tomar la Foto 2 y comparar.")
    print(" - Presiona Q para salir.\n")

    try:
        if args.auto:
            # Captura automática
            for step in (1, 2):
                # mostrar vista previa mientras espera
                t_start = time.time()
                while True:
                    ok, frame = cap.read()
                    if not ok:
                        frame = np.zeros((300, 600, 3), dtype=np.uint8)
                        put_text(frame, "ERROR leyendo cámara")
                    else:
                        msg = f"Capturando Foto {step}..."
                        if step == 2:
                            msg += f" en {max(0, int(args.delay - (time.time()-t_start)))} s"
                        put_text(frame, msg, 30)
                    cv2.imshow(win, frame)
                    if step == 1:
                        # tomar inmediatamente
                        break
                    else:
                        if time.time() - t_start >= args.delay:
                            break
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        return

                if step == 1:
                    photo1 = take_frame(cap, args.warmup)
                    cv2.imwrite(str(outdir / f"{ts_prefix}_photo1.png"), photo1)
                    print("[OK] Foto 1 capturada.")
                else:
                    photo2 = take_frame(cap, args.warmup)
                    cv2.imwrite(str(outdir / f"{ts_prefix}_photo2.png"), photo2)
                    print("[OK] Foto 2 capturada.")

        # Modo manual (teclas)
        while photo1 is None or photo2 is None:
            ok, frame = cap.read()
            if not ok or frame is None:
                frame = np.zeros((300, 600, 3), dtype=np.uint8)
                put_text(frame, "ERROR leyendo cámara")
            else:
                view = frame.copy()
                if photo1 is None:
                    put_text(view, "ESPACIO = Foto 1 | Q = Salir", 30)
                elif photo2 is None:
                    put_text(view, "ESPACIO = Foto 2 (comparar) | Q = Salir", 30)
                    # miniatura Foto 1
                    h, w = view.shape[:2]
                    thumb = cv2.resize(photo1, (w//5, h//5)) if photo1 is not None else None
                    if thumb is not None:
                        view[10:10+thumb.shape[0], 10:10+thumb.shape[1]] = thumb

            cv2.imshow(win, view if ok and frame is not None else frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                return
            if key == 32:  # ESPACIO
                if photo1 is None:
                    photo1 = take_frame(cap, args.warmup)
                    cv2.imwrite(str(outdir / f"{ts_prefix}_photo1.png"), photo1)
                    print("[OK] Foto 1 guardada.")
                elif photo2 is None:
                    photo2 = take_frame(cap, args.warmup)
                    cv2.imwrite(str(outdir / f"{ts_prefix}_photo2.png"), photo2)
                    print("[OK] Foto 2 guardada.")

        # Comparar
        mask, diff_col, changed, pct = compare_frames(
            photo1, photo2, blur=args.blur, thresh=args.thresh, morph=args.morph
        )
        print(f"[RESULTADO] Píxeles cambiados: {changed}  ({pct:.3f} %)")

        # Guardar y mostrar resultados
        fmask = outdir / f"{ts_prefix}_mask.png"
        fdiff = outdir / f"{ts_prefix}_diff.png"
        cv2.imwrite(str(fmask), mask)
        cv2.imwrite(str(fdiff), diff_col)

        vis1 = photo1.copy(); put_text(vis1, "Foto 1")
        vis2 = photo2.copy(); put_text(vis2, "Foto 2")
        vism = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR); put_text(vism, f"Mask ({pct:.2f}% cambio)")
        visd = diff_col.copy(); put_text(visd, "Diff coloreado (rojo=cambio)")

        cv2.imshow("Foto 1", vis1)
        cv2.imshow("Foto 2", vis2)
        cv2.imshow("Mask", vism)
        cv2.imshow("Diff", visd)

        print(f"[Archivos] Guardados en: {outdir.resolve()}")
        print("Pulsa Q en cualquier ventana para cerrar.")
        while True:
            if (cv2.waitKey(1) & 0xFF) == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

def parse_args():
    ap = argparse.ArgumentParser(description="Toma dos fotos con la webcam y compara cambios.")
    ap.add_argument("--camera", type=int, default=0, help="Índice de cámara (0 por defecto).")
    ap.add_argument("--width", type=int, default=1280, help="Ancho de captura.")
    ap.add_argument("--height", type=int, default=720, help="Alto de captura.")
    ap.add_argument("--thresh", type=int, default=25, help="Umbral (0-255) para detectar cambio.")
    ap.add_argument("--blur", type=int, default=5, help="Kernel de blur gaussiano (impar). 0=off.")
    ap.add_argument("--morph", type=int, default=3, help="Kernel morfológico. 0=off.")
    ap.add_argument("--warmup", type=float, default=0.25, help="Warmup antes de capturar (s).")
    ap.add_argument("--outdir", type=str, default="outputs", help="Carpeta de salida.")
    ap.add_argument("--dshow", action="store_true", help="Usar backend DirectShow (Windows).")
    ap.add_argument("--auto", action="store_true", help="Toma Foto 1 y 2 automáticamente (sin teclas).")
    ap.add_argument("--delay", type=float, default=3.0, help="Segundos entre Foto 1 y 2 en modo --auto.")
    return ap.parse_args()

if __name__ == "__main__":
    args = parse_args()
    try:
        run(args)
    except Exception as e:
        print("[ERROR]", e)
        print("\nSugerencias:")
        print(" - Prueba con --camera 1 (o 2) si tienes varias webcams.")
        print(" - Añade --dshow en Windows para mejor compatibilidad.")
        print(" - Cierra otras apps que usen la cámara (Teams/Zoom/etc.).")
        print(" - Ajusta --thresh (más alto = menos sensible a luz/ruido).")
        print(" - Cambia resolución: --width 640 --height 480.\n")
        sys.exit(1)
