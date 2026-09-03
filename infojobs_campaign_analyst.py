import pandas as pd
import streamlit as st
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
# CARGA DE DATOS
# =========================================================

def load_data(uploaded_file) -> pd.DataFrame:
    """
    Carga datos de campaña desde Excel o CSV.
    """

    filename = uploaded_file.name.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    return df


# =========================================================
# NORMALIZACIÓN DE COLUMNAS
# =========================================================

def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intenta estandarizar nombres habituales de columnas a:

    campaign
    imps
    clicks
    leads
    cost
    ctr
    cvr
    cpa
    """

    col_map = {}

    for col in df.columns:

        low = str(col).strip().lower()

        if "line item" in low or "campaign" in low or "puesto" in low:
            col_map[col] = "campaign"

        elif "imp" in low:
            col_map[col] = "imps"

        elif "click" in low:
            col_map[col] = "clicks"

        elif (
            "lead" in low
            or "candid" in low
            or "application" in low
        ):
            col_map[col] = "leads"

        elif (
            "total cost" in low
            or "total gasto" in low
            or low in ["cost", "costo", "gasto"]
        ):
            col_map[col] = "cost"

        elif low == "ctr":
            col_map[col] = "ctr"

        elif low == "cvr":
            col_map[col] = "cvr"

        elif low == "cpa":
            col_map[col] = "cpa"

    return df.rename(columns=col_map)


# =========================================================
# CÁLCULO DE MÉTRICAS
# =========================================================

def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:

    required_columns = ["imps", "clicks", "leads"]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Faltan columnas necesarias: {', '.join(missing)}"
        )

    numeric_columns = [
        "imps",
        "clicks",
        "leads",
        "cost",
        "ctr",
        "cvr",
        "cpa"
    ]

    for col in numeric_columns:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    # CTR
    if "ctr" not in df.columns:

        df["ctr"] = (
            df["clicks"] / df["imps"]
        ).where(
            df["imps"] > 0,
            0
        )

    # CVR
    if "cvr" not in df.columns:

        df["cvr"] = (
            df["leads"] / df["clicks"]
        ).where(
            df["clicks"] > 0,
            0
        )

    # CPA
    if "cost" in df.columns and "cpa" not in df.columns:

        df["cpa"] = (
            df["cost"] / df["leads"]
        ).where(
            df["leads"] > 0
        )

    return df


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
    return bytes(pdf.output())


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

        df = load_data(
            uploaded_file
        )

        df = normalise_columns(
            df
        )

        df = compute_metrics(
            df
        )

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
        # TABLA
        # =================================================

        st.header(
            "📋 Datos de campaña"
        )

        display_df = df.copy()

        if "ctr" in display_df.columns:

            display_df["CTR"] = (
                display_df["ctr"] * 100
            ).round(2).astype(str) + "%"

        if "cvr" in display_df.columns:

            display_df["CVR"] = (
                display_df["cvr"] * 100
            ).round(2).astype(str) + "%"

        if "cpa" in display_df.columns:

            display_df["CPA"] = (
                display_df["cpa"].round(2)
            )

        st.dataframe(
            display_df,
            use_container_width=True
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
