import cv2
import numpy as np
import time
import sys

def open_camera(index=0):
    """Abre la cámara con el mejor backend según SO."""
    backends = []
    if sys.platform == "darwin":              # macOS
        backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
    elif sys.platform.startswith("win"):      # Windows
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    else:                                     # Linux
        backends = [cv2.CAP_V4L2, cv2.CAP_ANY]

    for b in backends:
        cap = cv2.VideoCapture(index, b)
        if cap.isOpened():
            return cap
    return cv2.VideoCapture(index)

def capture_frame(cap, warmup=0.2, grabs=3):
    """Lee un frame estable (pequeño warmup + descartar frames en buffer)."""
    time.sleep(warmup)
    for _ in range(grabs):
        cap.grab()
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError("No se pudo leer la cámara.")
    return frame

def diff_changed_pixels(img1, img2, thresh=25):
    """
    Compara dos imágenes BGR del mismo tamaño.
    Retorna: mask binaria (cambios), cantidad de píxeles cambiados, diff en grises.
    """
    if img1.shape[:2] != img2.shape[:2]:
        raise ValueError("Las imágenes deben tener el mismo tamaño.")

    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    g1 = cv2.GaussianBlur(g1, (5,5), 0)
    g2 = cv2.GaussianBlur(g2, (5,5), 0)

    diff = cv2.absdiff(g1, g2)
    _, mask = cv2.threshold(diff, thresh, 255, cv2.THRESH_BINARY)

    kernel = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)

    changed = int(cv2.countNonZero(mask))
    return mask, changed, diff

def main():
    cap = open_camera(0)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir la cámara.")

    print("Preparando cámara…")
    _ = capture_frame(cap, 0.5)

    print("Tomando foto A…")
    imgA = capture_frame(cap, 0.1)

    print("Esperando 1.0s…")
    time.sleep(1.0)

    print("Tomando foto B…")
    imgB = capture_frame(cap, 0.1)

    print("Comparando…")
    mask, changed, diff = diff_changed_pixels(imgA, imgB, thresh=25)

    h, w = mask.shape
    total = h * w
    pct = 100.0 * changed / total
    print(f"Píxeles cambiados: {changed} de {total} ({pct:.2f}%)")

    cv2.imshow("Imagen A", imgA)
    cv2.imshow("Imagen B", imgB)
    cv2.imshow("Diferencia (grises)", diff)
    cv2.imshow("Cambios (mask binaria)", mask)

    print("Presiona 'q' para salir…")
    while True:
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
