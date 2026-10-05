import pandas as pd
import streamlit as st
import altair as alt
from fpdf import FPDF


# =========================================================
# CONFIGURACIÓN DE LA APP
# =========================================================

st.set_page_config(
    page_title="Analista de Campañas",
    page_icon="📊",
    layout="wide"
)

# =========================================================
# ESTILO VISUAL
# =========================================================

st.markdown("""
<style>

/* Fondo general */
.stApp {
    background:
        radial-gradient(circle at 15% 0%, rgba(124, 92, 252, 0.14), transparent 28%),
        radial-gradient(circle at 85% 5%, rgba(59, 130, 246, 0.10), transparent 25%),
        #0B0F19;
    color: #F8FAFC;
}

/* Anchura y espaciado */
.block-container {
    max-width: 1400px;
    padding-top: 3rem;
    padding-bottom: 4rem;
}

/* Títulos */
h1, h2, h3 {
    color: #F8FAFC !important;
}

h1 {
    font-weight: 750 !important;
    letter-spacing: -0.04em;
}

/* Texto general */
p, label {
    color: #CBD5E1 !important;
}

/* Tarjetas KPI */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #151D2E, #111827);
    border: 1px solid #263247;
    padding: 22px 24px;
    border-radius: 16px;
}

[data-testid="stMetric"]:hover {
    border-color: #7C5CFC;
}

[data-testid="stMetricLabel"] {
    color: #94A3B8 !important;
}

[data-testid="stMetricValue"] {
    color: #F8FAFC !important;
    font-weight: 700;
}

/* Subida de archivos */
[data-testid="stFileUploader"] {
    background: #131A2A;
    border: 1px solid #263247;
    border-radius: 16px;
    padding: 18px;
}

/* Expanders */
[data-testid="stExpander"] {
    background: #131A2A;
    border: 1px solid #263247;
    border-radius: 12px;
    margin-bottom: 10px;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border: 1px solid #263247;
    border-radius: 12px;
    overflow: hidden;
}

/* Botón de descarga */
.stDownloadButton > button {
    background: linear-gradient(135deg, #7C5CFC, #5B4AE8);
    color: white !important;
    border: none;
    border-radius: 10px;
    padding: 0.65rem 1.3rem;
    font-weight: 600;
}

.stDownloadButton > button:hover {
    border: none;
    box-shadow: 0 8px 24px rgba(124,92,252,0.30);
}

/* Separadores */
hr {
    border-color: #263247 !important;
}

/* Footer Streamlit */
footer {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
