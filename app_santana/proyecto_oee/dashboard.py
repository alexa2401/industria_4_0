import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils.indicadores import calcular_mtbf, calcular_mttr, calcular_oee

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Dashboard Industrial 4.0", layout="wide")
st.title("Dashboard de Desempeño Industrial")

# --- INPUT: URL DE BITÁCORA ---
st.sidebar.header("Configuración")
url_input = st.sidebar.text_input(
    "Ingresa el enlace de tu bitácora CSV:",
    placeholder="Pega aquí el link de Google Drive o de tu CSV público"
)

# --- CONVERTIR URL DE GOOGLE DRIVE A DESCARGA DIRECTA ---
def drive_to_direct(url):
    if "drive.google.com" in url and "/d/" in url:
        file_id = url.split("/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

# --- CARGAR DATOS ---
if url_input:
    st.info("Cargando datos desde la URL proporcionada...")
    url = drive_to_direct(url_input)

    try:
        df = pd.read_csv(url, sep=',', engine='python')
        st.success("Datos cargados correctamente.")
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.stop()
else:
    st.warning("Ingresa el link de la bitácora en la barra lateral para comenzar.")
    st.stop()

# --- CONVERSIÓN DE FECHAS ---
for col in ['inicio_falla', 'fin_falla', 'inicio_reparacion', 'fin_reparacion']:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# --- CÁLCULO DE INDICADORES ---
mtbf = calcular_mtbf(df)
mttr = calcular_mttr(df)
oee = calcular_oee(df)

# --- COLOR ANDON ---
def color_andon(valor, bueno, medio):
    if valor >= bueno:
        return "🟢"
    elif valor >= medio:
        return "🟡"
    else:
        return "🔴"

# --- PESTAÑAS PRINCIPALES ---
tabs = st.tabs(["Producción", "Mantenimiento", "Calidad"])

# ============================================================
# TAB 1: PRODUCCIÓN
# ============================================================
with tabs[0]:
    st.header("Indicadores de Producción")

    col1, col2, col3 = st.columns(3)
    col1.metric("MTBF (hrs)", f"{mtbf:.2f}")
    col2.metric("MTTR (hrs)", f"{mttr:.2f}")
    col3.metric("OEE (%)", f"{oee:.1f}")

    # --- Gauge para OEE ---
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=oee,
        title={'text': "OEE (%)"},
        gauge={'axis': {'range': [0, 100]},
               'bar': {'color': 'green' if oee >= 85 else 'yellow' if oee >= 60 else 'red'}}
    ))
    st.plotly_chart(fig_gauge, use_container_width=True)

    st.subheader("Tendencia de Tiempo Operativo")
    fig = px.line(df, x='inicio_falla', y='tiempo_operativo', title="Tiempo operativo por evento")
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 2: MANTENIMIENTO
# ============================================================
with tabs[1]:
    st.header("Indicadores de Mantenimiento")

    df['tiempo_entre_fallas'] = (df['inicio_falla'] - df['fin_reparacion'].shift(1)).dt.total_seconds() / 3600
    fig2 = px.bar(df, x='inicio_falla', y='tiempo_entre_fallas', title="Tiempo entre fallas (hrs)")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Últimos registros de mantenimiento")
    st.dataframe(df[['inicio_falla', 'fin_falla', 'inicio_reparacion', 'fin_reparacion']].tail(10))

# ============================================================
# TAB 3: CALIDAD
# ============================================================
with tabs[2]:
    st.header("Indicadores de Calidad")

    df['calidad'] = df['piezas_ok'] / (df['piezas_ok'] + df['piezas_defectuosas']) * 100
    calidad_promedio = df['calidad'].mean()

    col1, col2 = st.columns(2)
    col1.metric("Calidad Promedio (%)", f"{calidad_promedio:.1f}")
    col2.markdown(f"### Nivel de Calidad: {color_andon(calidad_promedio, 95, 85)}")

    fig3 = px.line(df, x='inicio_falla', y='calidad', title="Evolución del indicador de calidad (%)")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Detalle de piezas producidas")
    st.dataframe(df[['inicio_falla', 'piezas_ok', 'piezas_defectuosas', 'calidad']].tail(10))
