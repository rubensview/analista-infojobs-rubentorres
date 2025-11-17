
import pandas as pd

def load_data(file_path: str) -> pd.DataFrame:
    """
    Load campaign data from an Excel or CSV file.
    Expected columns (case-insensitive):
      - 'Line item' or 'Campaign'
      - 'Imps' or 'Impressions'
      - 'Clicks'
      - 'Leads' or 'Applications'
      - 'Total Cost' or 'Cost'
      - Optional: 'CTR', 'CVR', 'CPA'
    """
    if file_path.lower().endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    return df


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Try to standardise column names to:
      - 'campaign'
      - 'imps'
      - 'clicks'
      - 'leads'
      - 'cost'
      - 'ctr'
      - 'cvr'
      - 'cpa'
    """
    col_map = {}
    for col in df.columns:
        low = col.strip().lower()
        if 'line item' in low or 'campaign' in low or 'puesto' in low:
            col_map[col] = 'campaign'
        elif 'imp' in low:
            col_map[col] = 'imps'
        elif 'click' in low:
            col_map[col] = 'clicks'
        elif 'lead' in low or 'candid' in low or 'application' in low:
            col_map[col] = 'leads'
        elif 'total cost' in low or (('cost' in low or 'gasto' in low) and 'total' in low):
            col_map[col] = 'cost'
        elif low == 'cost' or low == 'costo':
            col_map[col] = 'cost'
        elif low == 'ctr':
            col_map[col] = 'ctr'
        elif low == 'cvr':
            col_map[col] = 'cvr'
        elif low == 'cpa':
            col_map[col] = 'cpa'
    df = df.rename(columns=col_map)
    return df


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute CTR, CVR and CPA if not present.
    CTR  = clicks / imps
    CVR  = leads / clicks
    CPA  = cost / leads
    """
    if 'imps' not in df or 'clicks' not in df or 'leads' not in df:
        raise ValueError("Missing one of required columns: 'imps', 'clicks', 'leads'")

    # Avoid division by zero using where + fillna
    if 'ctr' not in df:
        df['ctr'] = (df['clicks'] / df['imps']).where(df['imps'] > 0, 0)

    if 'cvr' not in df:
        df['cvr'] = (df['leads'] / df['clicks']).where(df['clicks'] > 0, 0)

    if 'cost' in df and 'cpa' not in df:
        df['cpa'] = (df['cost'] / df['leads']).where(df['leads'] > 0, None)

    return df


def print_overall_summary(df: pd.DataFrame) -> None:
    print("\n===== RESUMEN GENERAL =====")
    valid = df.copy()
    # remove rows with NaN CPA when computing mean CPA
    mean_ctr = valid['ctr'].mean()
    mean_cvr = valid['cvr'].mean()
    mean_cpa = valid['cpa'].dropna().mean() if 'cpa' in valid else None

    print(f"CTR medio: {mean_ctr:.4%}")
    print(f"CVR medio: {mean_cvr:.2%}")
    if mean_cpa is not None:
        print(f"CPA medio: {mean_cpa:.2f} €")

    # Rango orientativo
    print("\nRangos de referencia orientativos:")
    print("- CTR bueno: > 1%")
    print("- CVR bueno: 10% – 20%")
    print("- CPA bueno: < 10–15 € (depende del perfil)")


def show_top_bottom(df: pd.DataFrame, metric: str, top_n: int = 3) -> None:
    print(f"\n===== TOP y BOTTOM por {metric.upper()} =====")
    if metric not in df:
        print(f"No se encuentra la métrica '{metric}' en el dataframe.")
        return

    # Para CPA, lo mejor es más bajo
    if metric == 'cpa':
        best = df.nsmallest(top_n, metric)
        worst = df.nlargest(top_n, metric)
    else:
        best = df.nlargest(top_n, metric)
        worst = df.nsmallest(top_n, metric)

    print("\nMejores campañas:")
    for _, row in best.iterrows():
        print(f"- {row.get('campaign', 'N/A')} | {metric.upper()}: {row[metric]:.4f}")

    print("\Peores campañas:")
    for _, row in worst.iterrows():
        value = row[metric]
        if isinstance(value, float):
            print(f"- {row.get('campaign', 'N/A')} | {metric.upper()}: {value:.4f}")
        else:
            print(f"- {row.get('campaign', 'N/A')} | {metric.upper()}: {value}")


def diagnose_row(row, mean_ctr, mean_cvr, mean_cpa):
    """
    Simple heuristic diagnosis for a single campaign row.
    """
    issues = []

    ctr = row['ctr']
    cvr = row['cvr']
    cpa = row['cpa']

    # CTR diagnosis
    if ctr < mean_ctr * 0.6:
        issues.append("CTR muy bajo → poca atracción en el listado (título/beneficios mejorables).")

    # CVR diagnosis
    if cvr < mean_cvr * 0.6:
        issues.append("CVR bajo → muchos clics pero pocas candidaturas (oferta poco atractiva o requisitos mal planteados).")

    # CPA diagnosis (only if not NaN)
    if pd.notna(cpa) and cpa > mean_cpa * 1.5:
        issues.append("CPA muy alto → coste por candidatura poco eficiente, revisar inversión o segmentación.")

    if not issues:
        issues.append("Rendimiento equilibrado o por encima de la media.")

    return issues


def print_detailed_recommendations(df: pd.DataFrame) -> None:
    print("\n===== DIAGNÓSTICO Y RECOMENDACIONES =====")

    mean_ctr = df['ctr'].mean()
    mean_cvr = df['cvr'].mean()
    mean_cpa = df['cpa'].dropna().mean() if 'cpa' in df else None

    for _, row in df.iterrows():
        campaign = row.get('campaign', 'N/A')
        ctr = row['ctr']
        cvr = row['cvr']
        cpa = row['cpa']

        print("\n---")
        print(f"Campaña: {campaign}")
        print(f"CTR: {ctr:.4%} | CVR: {cvr:.2%} | CPA: {cpa if pd.notna(cpa) else 'N/A'} €")

        issues = diagnose_row(row, mean_ctr, mean_cvr, mean_cpa)
        for issue in issues:
            print(f"• {issue}")

        # Suggested actions based on issues
        print("Acciones sugeridas:")
        if "CTR muy bajo" in " ".join(issues):
            print("  - Probar nuevo título más concreto y con beneficio clave.")
            print("  - Añadir salario y beneficios claros en las primeras líneas.")
        if "CVR bajo" in " ".join(issues):
            print("  - Revisar requisitos (separar imprescindibles de deseables).")
            print("  - Asegurarse de que la oferta es coherente con el salario/beneficios.")
        if "CPA muy alto" in " ".join(issues):
            print("  - Reducir presupuesto temporalmente y optimizar antes de escalar.")
            print("  - Considerar pausar si tras ajustes sigue con CPA muy superior a la media.")
        if "Rendimiento equilibrado" in " ".join(issues):
            print("  - Candidata para escalar presupuesto o replicar estructura en otras campañas.")

        # Simple A/B test suggestions
        print("Ideas de test A/B:")
        print("  - Versión A: título racional (salario/contrato). Versión B: título emocional (proyecto/equipo).")
        print("  - Destacar beneficios arriba vs. abajo en la descripción.")
        print("  - Ajustar tono del copy: más directo vs. más descriptivo.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analista de campañas InfoJobs (rule-based).")
    parser.add_argument("file", help="Ruta al fichero Excel o CSV con los datos de campaña.")
    args = parser.parse_args()

    df = load_data(args.file)
    df = normalise_columns(df)
    df = compute_metrics(df)

    print_overall_summary(df)
    show_top_bottom(df, 'ctr')
    show_top_bottom(df, 'cvr')
    if 'cpa' in df:
        show_top_bottom(df, 'cpa')

    print_detailed_recommendations(df)


if __name__ == "__main__":
    main()
