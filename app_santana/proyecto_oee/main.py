import pandas as pd
from utils.indicadores import calcular_indicadores
from andon import verificar_alerta
import os

# --- CONFIGURACIÓN ---
# Puedes cambiar esta URL por la de tu bitácora en la nube (Drive, GitHub, Dropbox, etc.)
BITACORA_URL = "https://drive.google.com/uc?export=download&id=1jWmBwNZkAou9QTdlHKZV8xYMH5ow6yJV"
ARCHIVO_LOCAL = "datos/bitacora.csv"


def descarga_datos(url, destino):
    """Descarga el archivo CSV desde la nube."""
    try:
        df = pd.read_csv(url)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        df.to_csv(destino, index=False)
        print(f"✅ Bitácora descargada correctamente desde: {url}")
        return df
    except Exception as e:
        print("Error al descargar la bitácora:", e)
        return None


def muestra_resultados(indicadores):
    """Imprime los resultados de forma ordenada en consola."""
    print("\nIndicadores calculados:")
    for k, v in indicadores.items():
        print(f" - {k}: {v:.4f}")


def main():
    print("=== Sistema de Indicadores y Alerta ANDON ===")

    # 1️⃣ Descargar bitácora
    df = descarga_datos(BITACORA_URL, ARCHIVO_LOCAL)
    if df is None:
        return

    # 2️⃣ Calcul
