import pandas as pd
import streamlit as st


# ---------------------------------------------------------
# CONFIGURACIÓN DE LA APP
# ---------------------------------------------------------

st.set_page_config(
    page_title="Analista de Campañas",
    page_icon="📊",
    layout="wide"
)


# ---------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------

def load_data(uploaded_file) -> pd.DataFrame:
    """
    Load campaign data from an uploaded Excel or CSV file.
    """

    filename = uploaded_file.name.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    return df


# ---------------------------------------------------------
# NORMALIZACIÓN DE COLUMNAS
# ---------------------------------------------------------

def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise common campaign column names to:

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


# ---------------------------------------------------------
# CÁLCULO DE MÉTRICAS
# ---------------------------------------------------------

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

    # Convertimos las métricas a valores numéricos
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


# ---------------------------------------------------------
# DIAGNÓSTICO
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# RECOMENDACIONES
# ---------------------------------------------------------

def generate_actions(issues):

    actions = []

    joined = " ".join(issues)

    if "CTR muy bajo" in joined:

        actions.append(
            "Probar un nuevo título más concreto y atractivo."
        )

        actions.append(
            "Destacar salario, beneficios o propuesta de valor en las primeras líneas."
        )

    if "CVR bajo" in joined:

        actions.append(
            "Revisar requisitos y separar claramente imprescindibles de deseables."
        )

        actions.append(
            "Comprobar que salario, beneficios y condiciones son competitivos."
        )

    if "CPA muy alto" in joined:

        actions.append(
            "Reducir temporalmente la inversión mientras se optimiza la campaña."
        )

        actions.append(
            "Revisar segmentación, fuentes de tráfico y distribución del presupuesto."
        )

    if "Rendimiento equilibrado" in joined:

        actions.append(
            "Valorar incrementar presupuesto o replicar esta estructura en otras campañas."
        )

    return actions


# ---------------------------------------------------------
# INTERFAZ STREAMLIT
# ---------------------------------------------------------

def main():

    st.title("📊 Analista de Rendimiento de Campañas")

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
        type=["xlsx", "xls", "csv"]
    )

    if uploaded_file is None:

        st.info(
            "👆 Sube un archivo Excel o CSV para comenzar el análisis."
        )

        return

    try:

        # -------------------------------------------------
        # PROCESAMIENTO
        # -------------------------------------------------

        df = load_data(uploaded_file)

        df = normalise_columns(df)

        df = compute_metrics(df)

        st.success(
            f"Archivo cargado correctamente: {uploaded_file.name}"
        )


        # -------------------------------------------------
        # KPIs GENERALES
        # -------------------------------------------------

        st.header("📈 Resumen ejecutivo")

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
            if total_cost is not None
            and total_leads > 0
            else None
        )

        col1, col2, col3, col4 = st.columns(4)

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

        col5, col6 = st.columns(2)

        col5.metric(
            "Candidaturas / Leads",
            f"{total_leads:,.0f}"
        )

        if overall_cpa is not None:

            col6.metric(
                "CPA",
                f"{overall_cpa:.2f} €"
            )


        # -------------------------------------------------
        # TABLA
        # -------------------------------------------------

        st.header("📋 Datos de campaña")

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
                display_df["cpa"]
                .round(2)
            )

        st.dataframe(
            display_df,
            use_container_width=True
        )


        # -------------------------------------------------
        # TOP / BOTTOM CTR
        # -------------------------------------------------

        st.header("🏆 Mejores y peores campañas")

        col1, col2 = st.columns(2)

        with col1:

            st.subheader("Top CTR")

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
                    f"**{campaign}** — {row['ctr']:.2%}"
                )

        with col2:

            st.subheader("Bottom CTR")

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
                    f"**{campaign}** — {row['ctr']:.2%}"
                )


        # -------------------------------------------------
        # CVR
        # -------------------------------------------------

        col3, col4 = st.columns(2)

        with col3:

            st.subheader("Top CVR")

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
                    f"**{campaign}** — {row['cvr']:.2%}"
                )

        with col4:

            st.subheader("Bottom CVR")

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
                    f"**{campaign}** — {row['cvr']:.2%}"
                )


        # -------------------------------------------------
        # CPA
        # -------------------------------------------------

        if "cpa" in df.columns:

            st.subheader("💰 Eficiencia de CPA")

            valid_cpa = df.dropna(
                subset=["cpa"]
            )

            if not valid_cpa.empty:

                col5, col6 = st.columns(2)

                with col5:

                    st.write("**Mejor CPA**")

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

                    st.write("**Peor CPA**")

                    worst_cpa = valid_cpa.nlargest(
                        3,
                        "cpa"
                    )

                    for _, row in worst_cpa.iterrows():

                        st.write(
                            f"**{row.get('campaign', 'Campaña')}** "
                            f"— {row['cpa']:.2f} €"
                        )


        # -------------------------------------------------
        # DIAGNÓSTICO
        # -------------------------------------------------

        st.header("🧠 Diagnóstico y recomendaciones")

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

                col1, col2, col3 = st.columns(3)

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

                st.write("### Diagnóstico")

                for issue in issues:

                    st.write(
                        f"• {issue}"
                    )

                actions = generate_actions(
                    issues
                )

                st.write("### Acciones sugeridas")

                for action in actions:

                    st.write(
                        f"• {action}"
                    )

                st.write("### Ideas de test A/B")

                st.write(
                    "• Título racional basado en salario/contrato vs. "
                    "título emocional basado en proyecto/equipo."
                )

                st.write(
                    "• Beneficios destacados al principio vs. "
                    "al final de la descripción."
                )

                st.write(
                    "• Copy directo y conciso vs. "
                    "copy más descriptivo."
                )


        # -------------------------------------------------
        # DESCARGA
        # -------------------------------------------------

        st.header("📥 Exportar resultados")

        csv = df.to_csv(
            index=False
        ).encode(
            "utf-8"
        )

        st.download_button(
            label="Descargar análisis en CSV",
            data=csv,
            file_name="campaign_analysis.csv",
            mime="text/csv"
        )


    except Exception as e:

        st.error(
            "Se ha producido un error al procesar el archivo."
        )

        st.exception(e)


# ---------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------

if __name__ == "__main__":
    main()
