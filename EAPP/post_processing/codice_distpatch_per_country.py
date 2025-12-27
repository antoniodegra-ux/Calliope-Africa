# -*- coding: utf-8 -*-
"""
Pie chart per uno stato da results_carrier_prod.csv (valori in kWh):
- Aggrega Solar / Wind / Hydro / Fossil / Geothermal / Bioenergy / Storage
- Ignora linee interne allo stesso Stato
- Mostra solo import esterni = "Imports"
- Legenda con percentuali (senza GWh), nascondendo voci <0.5%
- Nessun titolo sul grafico
- Legenda con font grande
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from pathlib import Path

# ========= CONFIG =========
CSV_PATH = Path("/Users/antoniodegrazia/Desktop/run_2040_new_true/run_autarky/autarky_GT+VRES_2040_BESS/results/results_carrier_prod.csv")
STATE    = "Ethiopia"
OUT_DIR  = CSV_PATH.parent
PNG_OUT  = OUT_DIR / f"pie_{STATE}.png"
CSV_OUT  = OUT_DIR / f"pie_{STATE}_aggregated.csv"

IMPORTS_POSITIVE_AT_NODE = True
EPS_FRAC, EPS_ABS = 1e-8, 1e-4
LEGEND_FONTSIZE = 15  # 👈 font grande per la legenda

# Colori coerenti con la tesi (fossili marrone scuro)
COLORS = {
    "Solar": "#ffd34d",
    "Wind": "#cfe3ff",
    "Hydro": "#005580",
    "Geothermal": "#ff7f00",
    "Bioenergy": "#66a61e",
    "Fossil": "#8B4513",
    "BESS": "#b9d97c",
    "PHES": "#66c2a5",
    "Imports": "#999999"
}

LINK_REGEX = re.compile(r'(132|220|400|440|500).*kV|transmission|new[_-]*transmission',
                        re.IGNORECASE)


def smart_read_value_col(df: pd.DataFrame) -> str:
    for c in ["carrier_prod", "carrier_prod_sum", "value", "carrier_production"]:
        if c in df.columns:
            return c
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not num_cols:
        raise ValueError("Non trovo una colonna numerica dei valori.")
    return num_cols[-1]


def classify_macro_nonlink(tech: str) -> str:
    s = str(tech).upper()
    if ("PV" in s) or ("SOLAR" in s):
        return "Solar"
    if "WIND" in s:
        return "Wind"
    if ("HYDRO" in s) or ("RUN_OF_RIVER" in s) or ("ROR" in s) or ("HPP" in s):
        return "Hydro"
    if "GEOTHERM" in s:
        return "Geothermal"
    if "BIO" in s:
        return "Bioenergy"
    if any(x in s for x in ["OCGT", "CCGT", "DIESEL", "NG", "GAS", "COAL", "HFO", "FOSSIL"]):
        return "Fossil"
    if "BESS" in s:
        return "BESS"
    if "PHES" in s:
        return "PHES"
    return str(tech)


def load_and_filter(csv_path: Path, state: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    if "carriers" in df.columns:
        mask = df["carriers"].astype(str).str.contains("power|electric", case=False, na=False)
        if mask.any():
            df = df[mask].copy()

    loc_df = df[df["locs"].astype(str).str.startswith(f"{state}", na=False)].copy()
    if loc_df.empty:
        raise ValueError(f"Nessuna riga trovata per {state}")
    return loc_df


def build_aggregates(loc_df: pd.DataFrame, val_col: str, state: str) -> pd.DataFrame:
    df = loc_df.copy()
    results = []

    mask_links = df["techs"].str.contains(LINK_REGEX, na=False)
    nonlink = df[~mask_links].copy()
    if not nonlink.empty:
        nonlink["label"] = nonlink["techs"].apply(classify_macro_nonlink)
        gen = nonlink.groupby("label", as_index=False)[val_col].sum()
        gen = gen[gen[val_col] > 0].copy()
        gen.rename(columns={val_col: "value_kWh"}, inplace=True)
        results.append(gen)

    link = df[mask_links].copy()
    if not link.empty:
        imp_mask = (link[val_col] > 0) if IMPORTS_POSITIVE_AT_NODE else (link[val_col] < 0)
        link_imp = link[imp_mask].copy()

        def external_neighbor(tech):
            if ":" not in str(tech):
                return None
            neigh = str(tech).split(":")[-1]
            return None if neigh.startswith(state) else neigh

        link_imp["neighbor"] = link_imp["techs"].apply(external_neighbor)
        link_imp = link_imp[link_imp["neighbor"].notna()]

        if not link_imp.empty:
            imp_sum = link_imp[val_col].sum()
            results.append(pd.DataFrame({"label": ["Imports"], "value_kWh": [imp_sum]}))

    if results:
        pie_df = pd.concat(results, ignore_index=True)
    else:
        pie_df = pd.DataFrame(columns=["label", "value_kWh"])

    total = pie_df["value_kWh"].sum()
    eps = max(EPS_FRAC * max(total, 1.0), EPS_ABS)
    pie_df = pie_df[pie_df["value_kWh"].abs() > eps].copy()

    return pie_df.sort_values("value_kWh", ascending=False).reset_index(drop=True)


def plot_pie(pie_df: pd.DataFrame, state: str, png_out: Path):
    values = pie_df["value_kWh"].to_numpy(dtype=float)
    labels = pie_df["label"].tolist()

    total = values.sum()
    percents = values / total * 100 if total > 0 else np.zeros_like(values)

    colors = [COLORS.get(lab, "#cccccc") for lab in labels]

    plt.figure(figsize=(9, 7))
    wedges, _ = plt.pie(
        values,
        labels=None,
        startangle=90,
        counterclock=False,
        wedgeprops=dict(linewidth=0.8, edgecolor="white"),
        colors=colors
    )

    # Legenda solo percentuali, voci >0.5%
    legend_labels = []
    legend_handles = []
    for lab, pct, w in zip(labels, percents, wedges):
        if pct >= 0.5:
            legend_labels.append(f"{lab}: {pct:.1f}%")
            legend_handles.append(w)

    plt.legend(
        legend_handles,
        legend_labels,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=True,
        fontsize=LEGEND_FONTSIZE
    )

    plt.tight_layout()
    plt.savefig(png_out, dpi=240, bbox_inches="tight")
    plt.close()


def main():
    loc_df = load_and_filter(CSV_PATH, STATE)
    val_col = smart_read_value_col(loc_df)
    pie_df = build_aggregates(loc_df, val_col, STATE)

    out = pie_df.copy()
    out["value_GWh"] = out["value_kWh"] * 1e-6
    out = out[["label", "value_GWh"]]
    out.to_csv(CSV_OUT, index=False)

    plot_pie(pie_df, STATE, PNG_OUT)
    print(f"✅ Salvati:\n- Grafico: {PNG_OUT}\n- Aggregato: {CSV_OUT}")


if __name__ == "__main__":
    main()
