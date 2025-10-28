import pandas as pd
import numpy as np

def calcular_mtbf(df):
    """
    MTBF (Mean Time Between Failures) = Tiempo total operativo / Número de fallas
    """
    try:
        total_operativo = df['tiempo_operativo'].sum()
        n_fallas = len(df)
        if n_fallas == 0:
            return np.nan
        return total_operativo / n_fallas
    except KeyError:
        return np.nan


def calcular_mttr(df):
    """
    MTTR (Mean Time To Repair) = Tiempo total de reparación / Número de reparaciones
    """
    try:
        df['tiempo_reparacion'] = (df['fin_reparacion'] - df['inicio_reparacion']).dt.total_seconds() / 3600
        total_reparacion = df['tiempo_reparacion'].sum()
        n_reparaciones = df['tiempo_reparacion'].count()
        if n_reparaciones == 0:
            return np.nan
        return total_reparacion / n_reparaciones
    except KeyError:
        return np.nan


def calcular_mtta(df):
    """
    MTTA (Mean Time To Acknowledge) = Tiempo promedio en detectar una falla desde su inicio
    """
    try:
        df['tiempo_espera'] = (df['inicio_reparacion'] - df['inicio_falla']).dt.total_seconds() / 3600
        total_espera = df['tiempo_espera'].sum()
        n_fallas = df['tiempo_espera'].count()
        if n_fallas == 0:
            return np.nan
        return total_espera / n_fallas
    except KeyError:
        return np.nan


def calcular_confiabilidad(mtbf, tiempo_operacion):
    """
    Confiabilidad (R) = e^(-t / MTBF)
    """
    try:
        if mtbf == 0 or np.isnan(mtbf):
            return np.nan
        return np.exp(-tiempo_operacion / mtbf)
    except Exception:
        return np.nan


def calcular_disponibilidad(mtbf, mttr):
    """
    Disponibilidad = MTBF / (MTBF + MTTR)
    """
    try:
        if (mtbf + mttr) == 0 or np.isnan(mtbf) or np.isnan(mttr):
            return np.nan
        return (mtbf / (mtbf + mttr)) * 100
    except Exception:
        return np.nan


def calcular_desempeno(df):
    """
    Desempeño = Tiempo operativo real / Tiempo total planificado
    """
    try:
        tiempo_operativo = df['tiempo_operativo'].sum()
        tiempo_total = df['tiempo_total'].sum()
        if tiempo_total == 0:
            return np.nan
        return (tiempo_operativo / tiempo_total) * 100
    except KeyError:
        return np.nan


def calcular_calidad(df):
    """
    Calidad = Piezas OK / (Piezas OK + Piezas defectuosas)
    """
    try:
        total_ok = df['piezas_ok'].sum()
        total_def = df['piezas_defectuosas'].sum()
        total = total_ok + total_def
        if total == 0:
            return np.nan
        return (total_ok / total) * 100
    except KeyError:
        return np.nan


def calcular_oee(df):
    """
    OEE = Disponibilidad × Desempeño × Calidad
    """
    mtbf = calcular_mtbf(df)
    mttr = calcular_mttr(df)
    disponibilidad = calcular_disponibilidad(mtbf, mttr)
    desempeno = calcular_desempeno(df)
    calidad = calcular_calidad(df)

    try:
        oee = (disponibilidad / 100) * (desempeno / 100) * (calidad / 100) * 100
        return oee
    except Exception:
        return np.nan
