import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO
import xlsxwriter

st.set_page_config(page_title="Autoevaluación & Plan de Carrera", layout="wide")

# ------------------------------------------------------------------
# 1. CARGA DE DATOS BASE
# ------------------------------------------------------------------
FILE_BASE = "Valoracion_Jobs.xlsx"

@st.cache_data(show_spinner=True)
def load_base(path):
    df_comp = pd.read_excel(path, sheet_name="Competencias")
    df_beh_i = pd.read_excel(path, sheet_name="Comportamientos")[["Job Title", "IPE"]].drop_duplicates()

    def parse_ipe(val):
        if pd.isna(val): return np.nan
        s = str(val)
        if "-" in s:
            nums = [float(x) for x in s.split("-") if x.strip().isdigit()]
            return np.mean(nums) if nums else np.nan
        try:
            return float(s)
        except:
            return np.nan

    df_beh_i["IPE_val"] = df_beh_i["IPE"].apply(parse_ipe)
    df_comp = df_comp.merge(df_beh_i[["Job Title", "IPE_val"]], on="Job Title", how="left")
    return df_comp

try:
    df_comp = load_base(FILE_BASE)
except FileNotFoundError:
    st.error("⚠️ No se encontró 'Valoracion_Jobs.xlsx'. Sube el archivo al repositorio de la app.")
    st.stop()

competencias_cols = df_comp.columns[3:11].tolist()

# ------------------------------------------------------------------
# 2. MAPA DE COMPORTAMIENTOS
# ------------------------------------------------------------------
behaviors_map = {
    "Conocimientos técnicos": [],
    "Desarrollar nuestro negocio": [
        "Emprender, buscar y encontrar opciones mejores",
        "Hacer crecer el negocio",
        "Cumplir objetivos en el largo plazo",
        "Tomar decisiones",
        "Priorizar y decidir con velocidad",
        "Aplicar pensamiento estratégico y crear planes de negocio versátiles",
        "Usar datos para tomar decisiones",
    ],
    "Desarrollarse y contribuir al desarrollo de otr@s": [
        "Desarrollar conocimiento y nuevas habilidades",
        "Nutrir el talento",
        "Hacer crecer a los demás",
        "Estar disponible y accesible",
        "Hacer mentoring/coaching para maximizar el desempeño de los demás",
        "Asegurar la sucesión",
    ],
    "Navegar en lo desconocido": [
        "Buscar oportunidades y actuar",
        "Cuidar de la salud y el bienestar para conseguir un negocio sostenible",
        "Equilibrar la carga de trabajo",
        "Agradecer y celebrar con el equipo",
    ],
    "Generar resultados": [
        "Conseguir objetivos",
        "Pasión por los clientes y la decoración en el hogar",
        "Aplicar datos en el trabajo diario",
        "Simplificar y reducir costes, residuos y recursos para generar beneficios",
        "Hacer cumplir a los demás compromisos adquiridos",
        "Reconocer talentos",
        "Usar y hacer crecer el talento",
    ],
    "Comunicar con impacto": [
        "Comunicar de forma directa e inspiradora",
        "Dialogar con los demás",
        "Influir y hacer que las cosas sucedan",
        "Hacer que los demás entiendan su contribución en las estrategias de negocio",
    ],
    "Colaborar y co-crear": [
        "Crear equipos de alto rendimiento",
        "Hacer colaborar diferentes equipos, funciones, niveles, identidades y entornos",
    ],
    "Liderar con el ejemplo": [
        "Hacer que los demás lideren",
        "Hacer que la cultura y los valores sean parte del desempeño",
    ],
}

def behaviors_for_comp(col_name):
    clean_name = re.sub(r"^\d+\.\s*", "", col_name).strip()
    return behaviors_map.get(clean_name, [])

# ------------------------------------------------------------------
# 3. ENCABEZADO CON IMAGEN
# ------------------------------------------------------------------
col1, col2 = st.columns([1, 8])
with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135767.png", width=80)
with col2:
    st.title("Autoevaluación de Competencias y Comportamientos")

# ------------------------------------------------------------------
# 4. FORMULARIO DE AUTOEVALUACIÓN
# ------------------------------------------------------------------
nombre = st.text_input("Nombre completo")
areas_unique = sorted(df_comp["Area"].dropna().unique())
area_sel = st.selectbox("Área", ["-- Selecciona --"] + areas_unique)
puestos_sel = sorted(df_comp[df_comp["Area"] == area_sel]["Job Title"].unique()) if area_sel != "-- Selecciona --" else []
puesto = st.selectbox("Puesto actual", ["-- Selecciona --"] + puestos_sel)

# ------------------------------------------------------------------
# 5. COMPETENCIAS
# ------------------------------------------------------------------
st.header("1️⃣ Reparte 100 puntos entre las 8 competencias")
cols = st.columns(4)
comp_values = {comp: st.number_input(comp, 0, 100, 0, 1, key=f"comp_{i}") for i, comp in enumerate(competencias_cols)}
total_comp = sum(comp_values.values())
st.markdown(f"**Total asignado:** {total_comp} / 100")

# ------------------------------------------------------------------
# 6. COMPORTAMIENTOS
# ------------------------------------------------------------------
st.header("2️⃣ Evalúa los comportamientos (1‑5)")
beh_values = {}
for comp in competencias_cols:
    st.subheader(comp)
    for i, beh in enumerate(behaviors_for_comp(comp)):
        beh_values[beh] = st.slider(beh, 1, 5, 3, key=f"beh_{comp}_{i}")

# ------------------------------------------------------------------
# 7. PLAN DE CARRERA
# ------------------------------------------------------------------
if st.button("Generar plan de carrera"):
    if area_sel == "-- Selecciona --" or puesto == "-- Selecciona --":
        st.error("Selecciona tu área y puesto actual.")
        st.stop()
    if total_comp != 100:
        st.error("Distribuye exactamente 100 puntos entre las competencias.")
        st.stop()
    if not nombre:
        st.error("Por favor, introduce tu nombre.")
        st.stop()

    ipe_actual = df_comp.loc[df_comp["Job Title"] == puesto, "IPE_val"].iloc[0]
    st.success("✅ Plan de carrera generado")

    df_persona = pd.Series(comp_values)
    pesos = df_persona / 100

    resultados = []
    for _, row in df_comp.iterrows():
        if pd.isna(row["IPE_val"]) or row["IPE_val"] < ipe_actual:
            continue

        gap_comp = (abs(df_persona - row[competencias_cols]) * pesos).sum()

        gap_beh, n_beh = 0, 0
        for comp in competencias_cols:
            for beh in behaviors_for_comp(comp):
                gap_beh += abs(beh_values.get(beh, 3) - 5)
                n_beh += 1
        gap_beh = gap_beh / n_beh if n_beh else 0

        gap_total = 0.7 * gap_comp + 0.3 * gap_beh

        resultados.append({
            "Job Title": row["Job Title"],
            "Area": row["Area"],
            "IPE": row["IPE_val"],
            "Gap Total": round(gap_total, 2)
        })

    df_resultados = pd.DataFrame(resultados).drop_duplicates("Job Title").sort_values("Gap Total").reset_index(drop=True)
    st.subheader("🔍 Resultados del Plan de Carrera")
    st.dataframe(df_resultados, use_container_width=True)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_resultados.to_excel(writer, index=False, sheet_name="Plan de Carrera")
    st.download_button("📥 Descargar plan en Excel", data=buffer.getvalue(), file_name=f"plan_carrera_{nombre.replace(' ', '_')}.xlsx")
