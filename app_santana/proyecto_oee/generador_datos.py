import pandas as pd
import numpy as np
import os # Importamos la biblioteca os para manejar rutas de archivos
from datetime import datetime, timedelta

# Función para generar datos de prueba
def generar_datos_bitacora(num_filas, inicio_base):
    data = []
    for i in range(num_filas):
        # Generar fecha de inicio de falla
        inicio_falla = inicio_base + timedelta(days=i, hours=np.random.randint(7, 12), minutes=np.random.randint(0, 59))

        # Duración de la falla: 30 a 90 minutos
        duracion_falla = timedelta(minutes=np.random.randint(30, 90))
        fin_falla = inicio_falla + duracion_falla

        # Inicio de reparación: 5 a 15 minutos después de fin_falla
        retraso_reparacion = timedelta(minutes=np.random.randint(5, 15))
        inicio_reparacion = fin_falla + retraso_reparacion

        # Duración de la reparación: 20 a 50 minutos
        duracion_reparacion = timedelta(minutes=np.random.randint(20, 50))
        fin_reparacion = inicio_reparacion + duracion_reparacion

        # Piezas
        piezas_ok = np.random.randint(900, 1200)
        piezas_defectuosas = np.random.randint(20, 60)

        # Tiempos operativos y totales (simulación simple)
        tiempo_total = 8 # Asumimos jornadas de 8 horas
        # El tiempo operativo es el total menos el tiempo de inactividad
        tiempo_inactividad_horas = (duracion_falla + retraso_reparacion + duracion_reparacion).total_seconds() / 3600
        tiempo_operativo = max(0, tiempo_total - tiempo_inactividad_horas)

        # Formato de fecha y hora
        formato = '%d/%m/%Y %H:%M'

        data.append({
            'inicio_falla': inicio_falla.strftime(formato),
            'fin_falla': fin_falla.strftime(formato),
            'inicio_reparacion': inicio_reparacion.strftime(formato),
            'fin_reparacion': fin_reparacion.strftime(formato),
            'piezas_ok': piezas_ok,
            'piezas_defectuosas': piezas_defectuosas,
            'tiempo_operativo': round(tiempo_operativo, 2),
            'tiempo_total': tiempo_total
        })

    df = pd.DataFrame(data)
    return df

# La nueva ruta base donde se guardarán los archivos
RUTA_BASE = r'D:\7mo_semestre\Proyecto\industria_4_0\app_santana\proyecto_oee\datos'

# Crear el directorio si no existe
os.makedirs(RUTA_BASE, exist_ok=True)
print(f"Directorio de destino: '{RUTA_BASE}' (Creado si no existía).")

# Bases de fechas para simular diferentes períodos
bases_de_fecha = [
    datetime(2025, 10, 1),
    datetime(2025, 11, 1),
    datetime(2025, 12, 1),
    datetime(2026, 1, 1),
    datetime(2026, 2, 1)
]

# Generar y guardar 5 archivos CSV
nombres_archivos = [f'bitacora_prueba_{i+1}.csv' for i in range(5)]
num_datos = 50

print(f"Generando {len(nombres_archivos)} archivos CSV con {num_datos} filas cada uno...")

for i, base in enumerate(bases_de_fecha):
    df_prueba = generar_datos_bitacora(num_datos, base)
    
    # Combinamos la ruta base con el nombre del archivo
    ruta_completa_archivo = os.path.join(RUTA_BASE, nombres_archivos[i])
    
    # Guardamos el archivo en la ruta especificada
    df_prueba.to_csv(ruta_completa_archivo, index=False) # LÍNEA MODIFICADA
    print(f"✅ Archivo '{nombres_archivos[i]}' generado y guardado en:\n   {ruta_completa_archivo}")

print("\n¡Archivos de prueba listos y guardados en la ruta solicitada!")