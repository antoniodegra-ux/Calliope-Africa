# -*- coding: utf-8 -*-
"""
Pie charts: investimenti totali per stato (2030+2035+2040) per scenario
- Tecnologie conteggiate: ^PV_.*_MSR (no *_installed), ^Wind_.*_MSR (no *_installed),
                          OCGT_NG_new, BESS, PHES, new_transmission
- 12 grafici:
    * 6 scenari con stati aggregati (KEN, TAN, EGY, DRC)
    * 6 scenari con regioni non aggregate
- Slices < 1% raggruppate in 'Other'
- Legenda a lato; niente etichette sul pie
"""

from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ========= CONFIG =========
BASE_DIRS = {
    "2030": Path("/Users/antoniodegrazia/Desktop/run_2030_new_true"),
    "2035": Path("/Users/antoniodegrazia/Desktop/run_2035_new_true"),
    "2040": Path("/Users/antoniodegrazia/Desktop/run_2040_new_true"),
}
RESULTS_SUB = Path("results")
INV_FILE = "results_cost_investment.csv"

OUT_DIR = Path("/Users/antoniodegrazia/Desktop/planning/grafici/INV_PIE_FINALE")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# === Scenari ===
SCENARIOS = {
    "VRES_nostorage":     "existing_VRES_{y}_nostorage",
    "VRES_BESS":          "existing_VRES_{y}_BESS",
    "VRES_PHES":          "existing_VRES_{y}_PHES",
    "GT+VRES_nostorage":  "existing_GT+VRES_{y}_nostorage",
    "GT+VRES_BESS":       "existing_GT+VRES_{y}_BESS",
    "GT+VRES_PHES":       "existing_GT+VRES_{y}_PHES",
}

# Soglia per raggruppare in "Other" (frazione: 0.01 = 1%)
SMALL_THRESHOLD = 0.01

# ======= Pattern filtri investimenti =======
PV_NEW        = re.compile(r"^PV_.*_MSR",   re.IGNORECASE)
WIND_NEW      = re.compile(r"^Wind_.*_MSR", re.IGNORECASE)
INSTALLED_END = re.compile(r"_installed$",  re.IGNORECASE)

def normalize_state_agg(s: str) -> str:
    """Aggrega regioni in stati principali"""
    s = str(s).upper().split("_")[0]
    if s.startswith("KEN"): return "KEN"
    if s.startswith("TAN"): return "TAN"
    if s.startswith("EGY"): return "EGYPT"
    if s.startswith("DRC"): return "DRC"
    return s

def normalize_state_nonagg(s: str) -> str:
    """Mantiene regioni (KEN_N, TAN_S, EGY_N, DRC_E, etc.)"""
    return str(s).upper()

def read_costs_csv(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    if "costs" in df.columns:
        df = df[df["costs"].astype(str).str.lower().eq("monetary")]
    return df

def filter_and_prepare(df: pd.DataFrame, normalize_func) -> pd.DataFrame:
    """
    Filtra investimenti e restituisce B$ per stato/regione:
    - PV/Wind: ^PV_.*_MSR / ^Wind_.*_MSR  e  no *_installed
    - OCGT:    OCGT_NG_new
    - Storage: BESS, PHES
    - TX:      new_transmission
    """
    if df.empty or "techs" not in df.columns or "cost_investment" not in df.columns:
        return pd.DataFrame(columns=["state","invest_B$"])

    df = df.copy()
    df["techs"] = df["techs"].astype(str)
    df["cost_investment"] = pd.to_numeric(df["cost_investment"], errors="coerce").fillna(0.0)

    pv_mask   = df["techs"].str.match(PV_NEW)   & ~df["techs"].str.contains(INSTALLED_END)
    wind_mask = df["techs"].str.match(WIND_NEW) & ~df["techs"].str.contains(INSTALLED_END)
    ocgt_mask = df["techs"].eq("OCGT_NG_new")
    stor_mask = df["techs"].isin(["BESS","PHES"])
    tx_mask   = df["techs"].eq("new_transmission")

    df = df[pv_mask | wind_mask | ocgt_mask | stor_mask | tx_mask]

    if "locs" in df.columns:
        df["state"] = df["locs"].apply(normalize_func)
    else:
        ext = df["techs"].str.extract(r"^(?:PV|Wind|new_transmission)_([^_]+)", expand=False)
        df["state"] = ext.fillna("UNK").apply(normalize_func)

    out = df.groupby("state", as_index=False)["cost_investment"].sum()
    out["invest_B$"] = out["cost_investment"]/1e9
    return out[["state","invest_B$"]]

def collect_scenario_totals(base_dirs, scen_template: str, normalize_func) -> pd.DataFrame:
    """Somma investimenti 2030+2035+2040 per scenario (in B$)"""
    pieces = []
    for year, base in base_dirs.items():
        scen = scen_template.format(y=year)
        res_dir = base / "run_existing" / scen / RESULTS_SUB
        inv_path = res_dir / INV_FILE
        if not inv_path.exists():
            continue
        df_cost = read_costs_csv(inv_path)
        pieces.append(filter_and_prepare(df_cost, normalize_func))
    if not pieces:
        return pd.DataFrame(columns=["state","Total_B$"])
    df = pd.concat(pieces, ignore_index=True)
    df = df.groupby("state", as_index=False)["invest_B$"].sum().rename(columns={"invest_B$":"Total_B$"})
    # rimuovi stati a zero
    df = df[df["Total_B$"] > 0].reset_index(drop=True)
    return df

def group_small_slices(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Raggruppa voci con quota < soglia in 'Other'."""
    if df.empty:
        return df
    total = df["Total_B$"].sum()
    if total <= 0:
        return df
    df = df.copy()
    df["share"] = df["Total_B$"] / total
    small = df["share"] < threshold
    if small.any():
        other_sum = df.loc[small, "Total_B$"].sum()
        df = df.loc[~small, ["state","Total_B$"]]
        if other_sum > 0:
            df = pd.concat([df, pd.DataFrame([{"state":"Other", "Total_B$":other_sum}])], ignore_index=True)
    df = df.sort_values("Total_B$", ascending=False).reset_index(drop=True)
    return df

def plot_pie_with_legend(df: pd.DataFrame, title: str, out_path: Path):
    """Pie senza label; legenda a destra con valori e percentuali."""
    fig, ax = plt.subplots(figsize=(9,7))
    if df.empty or df["Total_B$"].sum() == 0:
        ax.text(0.5, 0.5, "No Data", ha="center", va="center")
        ax.axis("off")
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"⚠️ Vuoto: {out_path}")
        return

    values = df["Total_B$"].to_numpy()
    labels = df["state"].astype(str).tolist()
    total  = values.sum()
    # pie senza autopct e senza labels
    wedges, _ = ax.pie(values, startangle=90)

    # legenda a lato con label + % + B$
    pct = 100 * values / total
    legend_labels = [f"{lab}: {p:.1f}%  ({v:.2f} B$)" for lab, p, v in zip(labels, pct, values)]
    ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(1, 0.5), title="Share")

    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Salvato: {out_path}")

# ===== MAIN =====
for scen_name, scen_template in SCENARIOS.items():
    # Aggregated (KEN, TAN, EGY, DRC accorpati)
    df_agg = collect_scenario_totals(BASE_DIRS, scen_template, normalize_state_agg)
    df_agg = group_small_slices(df_agg, SMALL_THRESHOLD)
    plot_pie_with_legend(
        df_agg,
        f"{scen_name} – Investments by Country (Aggregated, 2030+2035+2040)",
        OUT_DIR / f"{scen_name}_pie_agg.png"
    )

    # Non-aggregated (regioni mantenute)
    df_non = collect_scenario_totals(BASE_DIRS, scen_template, normalize_state_nonagg)
    df_non = group_small_slices(df_non, SMALL_THRESHOLD)
    plot_pie_with_legend(
        df_non,
        f"{scen_name} – Investments by Region (Non-aggregated, 2030+2035+2040)",
        OUT_DIR / f"{scen_name}_pie_nonagg.png"
    )
