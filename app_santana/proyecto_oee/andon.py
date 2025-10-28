def verificar_alerta(indicadores):
    """
    Define umbrales mínimos de desempeño y devuelve lista de alertas.
    """
    alertas = []
    if indicadores['OEE'] < 0.85:
        alertas.append("Bajo OEE (<85%)")
    if indicadores['Disponibilidad'] < 0.90:
        alertas.append("Baja Disponibilidad")
    if indicadores['Calidad'] < 0.95:
        alertas.append("Problemas de Calidad")
    return alertas
