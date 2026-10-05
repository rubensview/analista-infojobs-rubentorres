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
# CARGA, NORMALIZACIÓN Y MÉTRICAS
# =========================================================

def _clean_name(value):
    return str(value).strip().lower().replace("_", " ")


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nombres y fusiona duplicados de forma segura."""
    df = df.copy()
    mapped = []

    for col in df.columns:
        low = _clean_name(col)

        if "advertiser" in low or "anunciante" in low:
            target = "advertiser"
        elif "salesrep" in low or "sales rep" in low:
            target = "salesrep"
        elif "profile" in low or "perfil" in low or "segmentación" in low or "segmentacion" in low:
            target = "profile"
        elif low in ["date", "fecha", "day", "día", "dia"] or "report date" in low:
            target = "date"
        elif "flight start" in low or "start date" in low or "fecha inicio" in low:
            target = "flight_start_date"
        elif "flight end" in low or "end date" in low or "fecha fin" in low:
            target = "flight_end_date"
        elif "line item" in low or low == "campaign" or "campaña" in low or "adops" in low:
            target = "campaign"
        elif low in ["imps", "imp", "impressions", "impresiones"] or "impression" in low:
            target = "imps"
        elif "click" in low or "clic" in low:
            target = "clicks"
        elif "lead" in low or "candid" in low or "application" in low:
            target = "leads"
        elif "revenue" in low or "ingreso" in low:
            target = "revenue"
        elif "total cost" in low or "total gasto" in low or low in ["cost", "costo", "gasto", "coste"]:
            target = "cost"
        elif low == "ctr":
            target = "ctr"
        elif low == "cvr":
            target = "cvr"
        elif low == "cpa":
            target = "cpa"
        else:
            target = col

        mapped.append(target)

    df.columns = mapped

    # Evita el error "Duplicate column names found".
    if df.columns.duplicated().any():
        result = pd.DataFrame(index=df.index)
        for name in pd.unique(df.columns):
            same = df.loc[:, df.columns == name]
            result[name] = same.iloc[:, 0] if same.shape[1] == 1 else same.bfill(axis=1).iloc[:, 0]
        df = result

    return df


def _to_number(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    s = series.astype(str).str.strip()
    s = s.str.replace("€", "", regex=False).str.replace("%", "", regex=False)
    s = s.str.replace("\u00a0", "", regex=False).str.replace(" ", "", regex=False)

    if s.str.contains(",", regex=False, na=False).any():
        s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)

    return pd.to_numeric(s, errors="coerce")


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    missing = [c for c in ["imps", "clicks", "leads"] if c not in df.columns]
    if missing:
        raise ValueError("Faltan columnas necesarias: " + ", ".join(missing))

    for col in ["imps", "clicks", "leads", "cost", "revenue", "ctr", "cvr", "cpa"]:
        if col in df.columns:
            df[col] = _to_number(df[col])

    # Recalcular siempre desde métricas base para evitar problemas de formato %.
    df["ctr"] = (df["clicks"] / df["imps"]).where(df["imps"] > 0, 0)
    df["cvr"] = (df["leads"] / df["clicks"]).where(df["clicks"] > 0, 0)

    if "cost" in df.columns:
        df["cpa"] = (df["cost"] / df["leads"]).where(df["leads"] > 0)

    return df


def load_data(uploaded_file):
    """
    Devuelve dos DataFrames:
      1. campañas agregadas
      2. datos diarios, si existen

    En Excel reconoce automáticamente hojas como 'Campañas' y 'Datos_Diarios'.
    """
    filename = uploaded_file.name.lower()

    if filename.endswith(".csv"):
        raw = normalise_columns(pd.read_csv(uploaded_file))
        campaign_df = compute_metrics(raw)
        daily_df = campaign_df.copy() if "date" in campaign_df.columns else None
        return campaign_df, daily_df

    uploaded_file.seek(0)
    sheets = pd.read_excel(uploaded_file, sheet_name=None)

    if not sheets:
        raise ValueError("El Excel no contiene hojas legibles.")

    sheets = {name: normalise_columns(data) for name, data in sheets.items()}

    campaign_df = None
    campaign_names = {"campañas", "campanas", "campaigns", "campaign", "resumen", "summary"}

    for name, data in sheets.items():
        if _clean_name(name) in campaign_names:
            campaign_df = data.copy()
            break

    if campaign_df is None:
        for data in sheets.values():
            if {"imps", "clicks", "leads"}.issubset(data.columns) and "date" not in data.columns:
                campaign_df = data.copy()
                break

    if campaign_df is None:
        campaign_df = next(iter(sheets.values())).copy()

    campaign_df = compute_metrics(campaign_df)

    daily_df = None
    daily_names = {"datos diarios", "datos diario", "datos daily", "daily", "daily data", "diario", "por día", "por dia"}

    for name, data in sheets.items():
        if _clean_name(name) in daily_names and "date" in data.columns:
            daily_df = data.copy()
            break

    if daily_df is None:
        for data in sheets.values():
            if "date" in data.columns and {"imps", "clicks"}.issubset(data.columns):
                daily_df = data.copy()
                break

    if daily_df is not None:
        if "leads" not in daily_df.columns:
            daily_df["leads"] = 0
        daily_df = compute_metrics(daily_df)

    return campaign_df, daily_df


# =========================================================
# DIAGNÓSTICO
# =========================================================

def diagnose_row(
    row,
    mean_ctr,
    mean_cvr,
    mean_cpa=None
):

    issues = []

    ctr = row.get("ctr", 0)
    cvr = row.get("cvr", 0)
    cpa = row.get("cpa", None)

    if pd.notna(ctr) and ctr < mean_ctr * 0.6:

        issues.append(
            "CTR muy bajo → poca atracción en el listado. "
            "Puede ser necesario revisar título, copy o beneficios."
        )

    if pd.notna(cvr) and cvr < mean_cvr * 0.6:

        issues.append(
            "CVR bajo → muchos clics pero pocas candidaturas. "
            "Puede existir fricción entre la oferta y las expectativas del usuario."
        )

    if (
        mean_cpa is not None
        and pd.notna(mean_cpa)
        and pd.notna(cpa)
        and cpa > mean_cpa * 1.5
    ):

        issues.append(
            "CPA muy alto → coste por candidatura poco eficiente. "
            "Conviene revisar inversión, segmentación o rendimiento del funnel."
        )

    if not issues:

        issues.append(
            "Rendimiento equilibrado o por encima de la media."
        )

    return issues


# =========================================================
# ACCIONES RECOMENDADAS
# =========================================================

def generate_actions(issues):

    actions = []

    joined = " ".join(issues)

    if "CTR muy bajo" in joined:

        actions.append(
            "Probar un nuevo título más concreto y atractivo."
        )

        actions.append(
            "Destacar salario, beneficios o propuesta de valor "
            "en las primeras líneas."
        )

    if "CVR bajo" in joined:

        actions.append(
            "Revisar requisitos y separar claramente "
            "imprescindibles de deseables."
        )

        actions.append(
            "Comprobar que salario, beneficios y condiciones "
            "son competitivos."
        )

    if "CPA muy alto" in joined:

        actions.append(
            "Reducir temporalmente la inversión mientras "
            "se optimiza la campaña."
        )

        actions.append(
            "Revisar segmentación, fuentes de tráfico "
            "y distribución del presupuesto."
        )

    if "Rendimiento equilibrado" in joined:

        actions.append(
            "Valorar incrementar presupuesto o replicar "
            "esta estructura en otras campañas."
        )

    return actions


# =========================================================
# LIMPIEZA DE TEXTO PARA PDF
# =========================================================

def clean_pdf_text(text):

    """
    Sustituye caracteres que pueden dar problemas
    con las fuentes estándar de FPDF.
    """

    replacements = {
        "→": "->",
        "–": "-",
        "—": "-",
        "•": "-",
        "€": "EUR",
        "“": '"',
        "”": '"',
        "’": "'"
    }

    text = str(text)

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


# =========================================================
# GENERACIÓN DEL INFORME EJECUTIVO PDF
# =========================================================

def generate_executive_pdf(
    df,
    total_imps,
    total_clicks,
    total_leads,
    overall_ctr,
    overall_cvr,
    overall_cpa
):

    pdf = FPDF()

    pdf.set_auto_page_break(
        auto=True,
        margin=15
    )

    pdf.add_page()

    # -----------------------------------------------------
    # CABECERA
    # -----------------------------------------------------

    pdf.set_font(
        "Arial",
        "B",
        18
    )

    pdf.cell(
        0,
        10,
        "CAMPAIGN PERFORMANCE",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "B",
        15
    )

    pdf.cell(
        0,
        9,
        "Executive Report",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        10
    )

    pdf.cell(
        0,
        7,
        "Automated campaign performance analysis",
        ln=True
    )

    pdf.ln(5)

    # -----------------------------------------------------
    # EXECUTIVE SUMMARY
    # -----------------------------------------------------

    pdf.set_font(
        "Arial",
        "B",
        14
    )

    pdf.cell(
        0,
        10,
        "1. Executive Summary",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        11
    )

    pdf.cell(
        0,
        7,
        f"Impressions: {total_imps:,.0f}",
        ln=True
    )

    pdf.cell(
        0,
        7,
        f"Clicks: {total_clicks:,.0f}",
        ln=True
    )

    pdf.cell(
        0,
        7,
        f"Leads / Applications: {total_leads:,.0f}",
        ln=True
    )

    pdf.cell(
        0,
        7,
        f"CTR: {overall_ctr:.2%}",
        ln=True
    )

    pdf.cell(
        0,
        7,
        f"CVR: {overall_cvr:.2%}",
        ln=True
    )

    if overall_cpa is not None:

        pdf.cell(
            0,
            7,
            f"CPA: {overall_cpa:.2f} EUR",
            ln=True
        )

    pdf.ln(5)

    # -----------------------------------------------------
    # PERFORMANCE OVERVIEW
    # -----------------------------------------------------

    pdf.set_font(
        "Arial",
        "B",
        14
    )

    pdf.cell(
        0,
        10,
        "2. Performance Overview",
        ln=True
    )

    # TOP CTR
    best_ctr = df.nlargest(
        3,
        "ctr"
    )

    pdf.set_font(
        "Arial",
        "B",
        11
    )

    pdf.cell(
        0,
        8,
        "Top campaigns by CTR",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        9
    )

    for _, row in best_ctr.iterrows():

        campaign = clean_pdf_text(
            row.get(
                "campaign",
                "Campaign"
            )
        )

        text = (
            f"- {campaign}: "
            f"{row['ctr']:.2%} CTR"
        )

        pdf.multi_cell(
            0,
            6,
            text
        )

    pdf.ln(3)

    # TOP CVR
    best_cvr = df.nlargest(
        3,
        "cvr"
    )

    pdf.set_font(
        "Arial",
        "B",
        11
    )

    pdf.cell(
        0,
        8,
        "Top campaigns by CVR",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        9
    )

    for _, row in best_cvr.iterrows():

        campaign = clean_pdf_text(
            row.get(
                "campaign",
                "Campaign"
            )
        )

        text = (
            f"- {campaign}: "
            f"{row['cvr']:.2%} CVR"
        )

        pdf.multi_cell(
            0,
            6,
            text
        )

    pdf.ln(3)

    # CAMPAÑAS A REVISAR
    worst_ctr = df.nsmallest(
        3,
        "ctr"
    )

    pdf.set_font(
        "Arial",
        "B",
        11
    )

    pdf.cell(
        0,
        8,
        "Campaigns requiring attention",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        9
    )

    for _, row in worst_ctr.iterrows():

        campaign = clean_pdf_text(
            row.get(
                "campaign",
                "Campaign"
            )
        )

        text = (
            f"- {campaign}: "
            f"{row['ctr']:.2%} CTR"
        )

        pdf.multi_cell(
            0,
            6,
            text
        )

    pdf.ln(5)

    # -----------------------------------------------------
    # KEY FINDINGS
    # -----------------------------------------------------

    pdf.set_font(
        "Arial",
        "B",
        14
    )

    pdf.cell(
        0,
        10,
        "3. Key Findings",
        ln=True
    )

    mean_ctr = df["ctr"].mean()
    mean_cvr = df["cvr"].mean()

    mean_cpa = (
        df["cpa"].dropna().mean()
        if "cpa" in df.columns
        else None
    )

    low_ctr_count = int(
        (
            df["ctr"] < mean_ctr * 0.6
        ).sum()
    )

    low_cvr_count = int(
        (
            df["cvr"] < mean_cvr * 0.6
        ).sum()
    )

    if (
        "cpa" in df.columns
        and mean_cpa is not None
        and pd.notna(mean_cpa)
    ):

        high_cpa_count = int(
            (
                df["cpa"] > mean_cpa * 1.5
            ).sum()
        )

    else:

        high_cpa_count = 0

    findings = [
        (
            f"{low_ctr_count} campaigns show CTR significantly "
            f"below the portfolio average."
        ),
        (
            f"{low_cvr_count} campaigns show CVR significantly "
            f"below the portfolio average."
        )
    ]

    if "cpa" in df.columns:

        findings.append(
            f"{high_cpa_count} campaigns show CPA significantly "
            f"above the portfolio average."
        )

    pdf.set_font(
        "Arial",
        "",
        10
    )

    for finding in findings:

        pdf.multi_cell(
            0,
            7,
            clean_pdf_text(
                f"- {finding}"
            )
        )

    pdf.ln(5)

    # -----------------------------------------------------
    # PRIORITY CAMPAIGNS
    # -----------------------------------------------------

    pdf.set_font(
        "Arial",
        "B",
        14
    )

    pdf.cell(
        0,
        10,
        "4. Priority Optimisation Opportunities",
        ln=True
    )

    problem_campaigns = []

    for _, row in df.iterrows():

        issues = diagnose_row(
            row,
            mean_ctr,
            mean_cvr,
            mean_cpa
        )

        if (
            "Rendimiento equilibrado"
            not in " ".join(issues)
        ):

            problem_campaigns.append(
                (
                    row.get(
                        "campaign",
                        "Campaign"
                    ),
                    issues
                )
            )

    pdf.set_font(
        "Arial",
        "",
        9
    )

    if problem_campaigns:

        for campaign, issues in problem_campaigns[:5]:

            campaign = clean_pdf_text(
                campaign
            )

            pdf.set_font(
                "Arial",
                "B",
                9
            )

            pdf.multi_cell(
                0,
                6,
                campaign
            )

            pdf.set_font(
                "Arial",
                "",
                9
            )

            for issue in issues:

                pdf.multi_cell(
                    0,
                    6,
                    clean_pdf_text(
                        f"- {issue}"
                    )
                )

            pdf.ln(2)

    else:

        pdf.multi_cell(
            0,
            6,
            "No major performance issues were identified."
        )

    pdf.ln(4)

    # -----------------------------------------------------
    # RECOMMENDACIONES
    # -----------------------------------------------------

    pdf.set_font(
        "Arial",
        "B",
        14
    )

    pdf.cell(
        0,
        10,
        "5. Recommended Actions",
        ln=True
    )

    recommendations = [
        (
            "Review campaigns with CTR materially below average "
            "and test alternative creative, messaging or positioning."
        ),
        (
            "Analyse campaigns with strong CTR but weak CVR "
            "to identify friction between traffic quality and conversion."
        ),
        (
            "Prioritise budget towards campaigns combining "
            "strong CTR, CVR and efficient CPA."
        ),
        (
            "Reduce or temporarily limit investment in persistent "
            "underperformers while optimisation tests are implemented."
        ),
        (
            "Replicate audience, format and campaign structures "
            "from the strongest-performing campaigns."
        )
    ]

    pdf.set_font(
        "Arial",
        "",
        10
    )

    for rec in recommendations:

        pdf.multi_cell(
            0,
            7,
            clean_pdf_text(
                f"- {rec}"
            )
        )

    pdf.ln(5)

    # -----------------------------------------------------
    # CONCLUSIÓN
    # -----------------------------------------------------

    pdf.set_font(
        "Arial",
        "B",
        14
    )

    pdf.cell(
        0,
        10,
        "6. Conclusion",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        10
    )

    conclusion = (
        "The analysis highlights opportunities to improve campaign "
        "efficiency by reallocating investment towards stronger "
        "performers while reviewing campaigns with weaker engagement, "
        "conversion or acquisition costs. Continuous testing and "
        "optimisation should be used to validate these recommendations "
        "before scaling investment."
    )

    pdf.multi_cell(
        0,
        7,
        conclusion
    )

    pdf.ln(8)

    pdf.set_font(
        "Arial",
        "I",
        8
    )

    pdf.multi_cell(
        0,
        5,
        "Report automatically generated by Campaign Performance Analyzer."
    )

    # FPDF devuelve bytearray en algunas versiones
    return pdf.output(dest="S").encode("latin-1")


# =========================================================
# INTERFAZ STREAMLIT
# =========================================================

def main():

    st.title(
        "📊 Analista de Rendimiento de Campañas"
    )

    st.write(
        """
        Sube un archivo Excel o CSV con los datos de campaña.

        La herramienta analizará automáticamente el rendimiento,
        calculará los principales KPIs e identificará oportunidades
        de optimización.
        """
    )

    uploaded_file = st.file_uploader(
        "Sube tu archivo de campaña",
        type=[
            "xlsx",
            "xls",
            "csv"
        ]
    )

    if uploaded_file is None:

        st.info(
            "👆 Sube un archivo Excel o CSV para comenzar el análisis."
        )

        return

    try:

        # =================================================
        # PROCESAMIENTO
        # =================================================

        df, daily_df = load_data(uploaded_file)
        daily_filtered = daily_df.copy() if daily_df is not None else None

        # =================================================
        # FILTROS
        # =================================================

        st.subheader("🔎 Filtros")

        if "advertiser" in df.columns:
            advertisers = sorted(
                df["advertiser"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            advertiser_selected = st.selectbox(
                "Advertiser",
                ["Todos"] + advertisers
            )

            if advertiser_selected != "Todos":
                df = df[
                    df["advertiser"].astype(str) == advertiser_selected
                ].copy()

                if daily_filtered is not None and "advertiser" in daily_filtered.columns:
                    daily_filtered = daily_filtered[
                        daily_filtered["advertiser"].astype(str) == advertiser_selected
                    ].copy()

        else:
            st.caption(
                "El archivo no contiene una columna de advertiser/anunciante."
            )

        if df.empty:
            st.warning("No hay datos para los filtros seleccionados.")
            return

        st.success(
            f"Archivo cargado correctamente: {uploaded_file.name}"
        )

        # =================================================
        # KPIs GENERALES
        # =================================================

        st.header(
            "📈 Resumen ejecutivo"
        )

        total_imps = df["imps"].sum()

        total_clicks = df["clicks"].sum()

        total_leads = df["leads"].sum()

        overall_ctr = (
            total_clicks / total_imps
            if total_imps > 0
            else 0
        )

        overall_cvr = (
            total_leads / total_clicks
            if total_clicks > 0
            else 0
        )

        total_cost = (
            df["cost"].sum()
            if "cost" in df.columns
            else None
        )

        overall_cpa = (
            total_cost / total_leads
            if (
                total_cost is not None
                and total_leads > 0
            )
            else None
        )

        col1, col2, col3, col4 = st.columns(
            4
        )

        col1.metric(
            "Impresiones",
            f"{total_imps:,.0f}"
        )

        col2.metric(
            "Clicks",
            f"{total_clicks:,.0f}"
        )

        col3.metric(
            "CTR",
            f"{overall_ctr:.2%}"
        )

        col4.metric(
            "CVR",
            f"{overall_cvr:.2%}"
        )

        col5, col6 = st.columns(
            2
        )

        col5.metric(
            "Candidaturas / Leads",
            f"{total_leads:,.0f}"
        )

        if overall_cpa is not None:

            col6.metric(
                "CPA",
                f"{overall_cpa:.2f} €"
            )

        # =================================================
        # VISUALIZACIONES
        # =================================================

        st.header("📊 Visualización del rendimiento")

        # -------------------------------------------------
        # IMPRESIONES POR PERFIL
        # -------------------------------------------------

        if "profile" in df.columns:

            profile_data = (
                df.groupby("profile", dropna=False)["imps"]
                .sum()
                .reset_index()
            )

            profile_data["profile"] = (
                profile_data["profile"]
                .fillna("Sin perfil")
                .astype(str)
            )

            profile_data["share"] = (
                profile_data["imps"] /
                profile_data["imps"].sum()
            )

            st.subheader("Distribución de impresiones por perfil")

            pie_chart = (
    alt.Chart(profile_data)
    .mark_arc(
        innerRadius=65,
        outerRadius=125
    )
    .encode(
        theta=alt.Theta(
            field="imps",
            type="quantitative"
        ),
        color=alt.Color(
            field="profile",
            type="nominal",
            title="Perfil",
            legend=alt.Legend(
                labelColor="#E5E7EB",
                titleColor="#FFFFFF",
                labelFontSize=13,
                titleFontSize=14
            )
        ),
        tooltip=[
            alt.Tooltip(
                "profile:N",
                title="Perfil"
            ),
            alt.Tooltip(
                "imps:Q",
                title="Impresiones",
                format=","
            ),
            alt.Tooltip(
                "share:Q",
                title="% del total",
                format=".1%"
            )
        ]
    )
    .properties(
        height=380
    )
    .configure_view(
        strokeWidth=0
    )
    .configure(
        background="transparent"
    )
)

            st.altair_chart(
                pie_chart,
                use_container_width=True,
                theme=None
            )

        else:

            st.info(
                "Para mostrar el gráfico de impresiones por perfil, "
                "el archivo debe incluir una columna 'Profile' o 'Perfil'."
            )

        # -------------------------------------------------
        # IMPRESIONES Y CTR POR DÍA
        # -------------------------------------------------

        if daily_filtered is not None and "date" in daily_filtered.columns:

            daily_source = daily_filtered.copy()

            daily_source["date"] = pd.to_datetime(
                daily_source["date"],
                errors="coerce",
                dayfirst=True
            )

            daily_source = daily_source.dropna(
                subset=["date"]
            )

            if not daily_source.empty:

                daily_data = (
                    daily_source
                    .groupby(
                        daily_source["date"].dt.date,
                        as_index=False
                    )
                    .agg(
                        imps=("imps", "sum"),
                        clicks=("clicks", "sum")
                    )
                )

                daily_data["date"] = pd.to_datetime(
                    daily_data["date"]
                )

                daily_data["ctr"] = (
                    daily_data["clicks"] /
                    daily_data["imps"]
                ).where(
                    daily_data["imps"] > 0,
                    0
                )

                st.subheader("Impresiones y CTR por día")

                base = alt.Chart(
                    daily_data
                ).encode(
                    x=alt.X(
                        "date:T",
                        title="Fecha",
                        axis=alt.Axis(
                            format="%d/%m",
                            labelAngle=-45
                        )
                    )
                )

                bars = base.mark_bar(
                    opacity=0.75
                ).encode(
                    y=alt.Y(
                        "imps:Q",
                        title="Impresiones"
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "date:T",
                            title="Fecha",
                            format="%d/%m/%Y"
                        ),
                        alt.Tooltip(
                            "imps:Q",
                            title="Impresiones",
                            format=","
                        )
                    ]
                )

                ctr_line = base.mark_line(
                    point=True,
                    strokeWidth=3
                ).encode(
                    y=alt.Y(
                        "ctr:Q",
                        title="CTR",
                        axis=alt.Axis(
                            format=".1%"
                        )
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "date:T",
                            title="Fecha",
                            format="%d/%m/%Y"
                        ),
                        alt.Tooltip(
                            "ctr:Q",
                            title="CTR",
                            format=".2%"
                        )
                    ]
                )

                combined_chart = (
                    alt.layer(
                        bars,
                        ctr_line
                    )
                    .resolve_scale(
                        y="independent"
                    )
                    .properties(
                        height=420
                    )
                )

                st.altair_chart(
                    combined_chart.configure(
                        background="transparent"
                    ).configure_view(
                        strokeWidth=0
                    ).configure_axis(
                        labelColor="#CBD5E1",
                        titleColor="#F8FAFC",
                        gridColor="#263247",
                        domainColor="#475569"
                    ),
                    use_container_width=True,
                    theme=None
                )

            else:

                st.info(
                    "La columna de fecha existe, pero no contiene "
                    "fechas válidas para construir el gráfico diario."
                )

        else:

            st.info(
                "Para mostrar impresiones y CTR por día, "
                "el archivo debe incluir una columna 'Date', 'Fecha' o 'Day'."
            )

        # =================================================
        # TABLA
        # =================================================

        st.header(
            "📋 Datos de campaña"
        )

        display_df = df.copy()

        # Formateamos las columnas existentes en lugar de crear CTR/CVR/CPA
        # adicionales, evitando nombres duplicados.
        if "ctr" in display_df.columns:
            display_df["ctr"] = display_df["ctr"].map(
                lambda x: f"{x:.2%}" if pd.notna(x) else ""
            )

        if "cvr" in display_df.columns:
            display_df["cvr"] = display_df["cvr"].map(
                lambda x: f"{x:.2%}" if pd.notna(x) else ""
            )

        if "cpa" in display_df.columns:
            display_df["cpa"] = display_df["cpa"].map(
                lambda x: f"{x:.2f} €" if pd.notna(x) else ""
            )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        # =================================================
        # MEJORES Y PEORES CAMPAÑAS
        # =================================================

        st.header(
            "🏆 Mejores y peores campañas"
        )

        col1, col2 = st.columns(
            2
        )

        with col1:

            st.subheader(
                "Top CTR"
            )

            top_ctr = df.nlargest(
                3,
                "ctr"
            )

            for _, row in top_ctr.iterrows():

                campaign = row.get(
                    "campaign",
                    "Campaña"
                )

                st.write(
                    f"**{campaign}** — "
                    f"{row['ctr']:.2%}"
                )

        with col2:

            st.subheader(
                "Bottom CTR"
            )

            bottom_ctr = df.nsmallest(
                3,
                "ctr"
            )

            for _, row in bottom_ctr.iterrows():

                campaign = row.get(
                    "campaign",
                    "Campaña"
                )

                st.write(
                    f"**{campaign}** — "
                    f"{row['ctr']:.2%}"
                )

        col3, col4 = st.columns(
            2
        )

        with col3:

            st.subheader(
                "Top CVR"
            )

            top_cvr = df.nlargest(
                3,
                "cvr"
            )

            for _, row in top_cvr.iterrows():

                campaign = row.get(
                    "campaign",
                    "Campaña"
                )

                st.write(
                    f"**{campaign}** — "
                    f"{row['cvr']:.2%}"
                )

        with col4:

            st.subheader(
                "Bottom CVR"
            )

            bottom_cvr = df.nsmallest(
                3,
                "cvr"
            )

            for _, row in bottom_cvr.iterrows():

                campaign = row.get(
                    "campaign",
                    "Campaña"
                )

                st.write(
                    f"**{campaign}** — "
                    f"{row['cvr']:.2%}"
                )

        # =================================================
        # CPA
        # =================================================

        if "cpa" in df.columns:

            st.subheader(
                "💰 Eficiencia de CPA"
            )

            valid_cpa = df.dropna(
                subset=["cpa"]
            )

            if not valid_cpa.empty:

                col5, col6 = st.columns(
                    2
                )

                with col5:

                    st.write(
                        "**Mejor CPA**"
                    )

                    best_cpa = valid_cpa.nsmallest(
                        3,
                        "cpa"
                    )

                    for _, row in best_cpa.iterrows():

                        st.write(
                            f"**{row.get('campaign', 'Campaña')}** "
                            f"— {row['cpa']:.2f} €"
                        )

                with col6:

                    st.write(
                        "**Peor CPA**"
                    )

                    worst_cpa = valid_cpa.nlargest(
                        3,
                        "cpa"
                    )

                    for _, row in worst_cpa.iterrows():

                        st.write(
                            f"**{row.get('campaign', 'Campaña')}** "
                            f"— {row['cpa']:.2f} €"
                        )

        # =================================================
        # DIAGNÓSTICO
        # =================================================

        st.header(
            "🧠 Diagnóstico y recomendaciones"
        )

        mean_ctr = df["ctr"].mean()

        mean_cvr = df["cvr"].mean()

        mean_cpa = (
            df["cpa"].dropna().mean()
            if "cpa" in df.columns
            else None
        )

        for _, row in df.iterrows():

            campaign = row.get(
                "campaign",
                "Campaña"
            )

            with st.expander(
                f"📌 {campaign}"
            ):

                ctr = row.get(
                    "ctr",
                    0
                )

                cvr = row.get(
                    "cvr",
                    0
                )

                cpa = row.get(
                    "cpa",
                    None
                )

                col1, col2, col3 = st.columns(
                    3
                )

                col1.metric(
                    "CTR",
                    f"{ctr:.2%}"
                )

                col2.metric(
                    "CVR",
                    f"{cvr:.2%}"
                )

                if pd.notna(cpa):

                    col3.metric(
                        "CPA",
                        f"{cpa:.2f} €"
                    )

                else:

                    col3.metric(
                        "CPA",
                        "N/A"
                    )

                issues = diagnose_row(
                    row,
                    mean_ctr,
                    mean_cvr,
                    mean_cpa
                )

                st.write(
                    "### Diagnóstico"
                )

                for issue in issues:

                    st.write(
                        f"• {issue}"
                    )

                actions = generate_actions(
                    issues
                )

                st.write(
                    "### Acciones sugeridas"
                )

                for action in actions:

                    st.write(
                        f"• {action}"
                    )

                st.write(
                    "### Ideas de test A/B"
                )

                st.write(
                    "• Título racional basado en salario/contrato "
                    "vs. título emocional basado en proyecto/equipo."
                )

                st.write(
                    "• Beneficios destacados al principio "
                    "vs. al final de la descripción."
                )

                st.write(
                    "• Copy directo y conciso "
                    "vs. copy más descriptivo."
                )

        # =================================================
        # EXPORTACIÓN
        # =================================================

        st.header(
            "📥 Exportar resultados"
        )

        col_csv, col_pdf = st.columns(
            2
        )

        # -------------------------------------------------
        # CSV
        # -------------------------------------------------

        csv = df.to_csv(
            index=False
        ).encode(
            "utf-8"
        )

        with col_csv:

            st.download_button(
                label="📊 Descargar datos analizados CSV",
                data=csv,
                file_name="campaign_analysis.csv",
                mime="text/csv",
                use_container_width=True
            )

        # -------------------------------------------------
        # PDF
        # -------------------------------------------------

        pdf_bytes = generate_executive_pdf(
            df=df,
            total_imps=total_imps,
            total_clicks=total_clicks,
            total_leads=total_leads,
            overall_ctr=overall_ctr,
            overall_cvr=overall_cvr,
            overall_cpa=overall_cpa
        )

        with col_pdf:

            st.download_button(
                label="📄 Descargar informe ejecutivo PDF",
                data=pdf_bytes,
                file_name="campaign_executive_report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    except Exception as e:

        st.error(
            "Se ha producido un error al procesar el archivo."
        )

        st.exception(
            e
        )


# =========================================================
# EJECUCIÓN
# =========================================================

if __name__ == "__main__":
    main()
