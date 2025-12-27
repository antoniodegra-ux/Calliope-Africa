# -*- coding: utf-8 -*-
"""
Autarky 2030 — 6 PNG separati: barre per area (paese/regione) con stack OCGT/Wind/PV/Storage
- Ascissa: aree (es. DRC_E, DRC_S, EGY_N, KEN, TAN_S, ...)
- Stack categorie: OCGT, Wind, PV, Storage
- Etichette col totale colonna in B$ sopra ogni barra
- Filtri:
  * PV/Wind: SOLO ^PV_.*_MSR / ^Wind_.*_MSR, ESCLUDE *_installed
  * Storage: SOLO 'BESS' e 'PHES' (no *_installed)
  * Transmission: esclusa
- Scenari: VRES/GT × N/B/P in BASE_2030/run_autarky/
"""

from pathlib import Path
import os, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ========= CONFIG =========
BASE_2030 = Path(r"C:\Users\ilari\OneDrive\Desktop\tesi\2030_true\run_2030_new_contrue")
RESULTS_SUB = Path("results")
INV_FILE = "results_cost_investment.csv"

OUT_DIR  = Path(r"C:\Users\ilari\OneDrive\Desktop\tesi\GRAFICI\INV BY COUNTRY\BARS_2030")
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEBUG = True

# Colori (coerenti)
COL = {"OCGT":"#f4b6b6", "Wind":"#cfe3ff", "PV":"#ffd34d", "Storage":"#b9d97c"}

def dprint(*a):
    if DEBUG: print(*a)

# Pattern per NUOVE build e per esclusione installed
PV_NEW        = re.compile(r"^PV_.*_MSR",   re.IGNORECASE)
WIND_NEW      = re.compile(r"^Wind_.*_MSR", re.IGNORECASE)
INSTALLED_END = re.compile(r"_installed$",  re.IGNORECASE)

# Estrai blocco paese[_regione] dal tech: PV_<PAESE[_REG]>_MSR...
TECH_BLOCK = re.compile(r"^(?:PV|Wind)_([^_]+(?:_[^_]+)*)_MSR", re.IGNORECASE)

def read_costs_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "costs" in df.columns:
        df = df[df["costs"].astype(str).str.lower().eq("monetary")]
    return df

def get_area_from_row(row) -> str:
    """
    NON aggrega le regioni:
    - se 'locs' esiste: usa l'intero valore (es. 'DRC_E', 'EGY_N', 'KEN', 'TAN_S')
    - altrimenti dal 'techs' prendi il blocco tra PV_/Wind_ e _MSR (es. 'DRC_S', 'KEN')
    """
    loc = str(row.get("locs", "")).strip()
    if loc and loc.lower() != "nan":
        return loc.upper()
    tech = str(row.get("techs", "")).strip()
    m = TECH_BLOCK.match(tech)
    if m:
        return m.group(1).upper()
    return "UNK"

def aggregate_investments_by_area(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ritorna DataFrame: area, PV, Wind, OCGT, Storage (B$).
    Applica filtri: PV/Wind solo nuove build, niente *_installed; Storage solo BESS/PHES.
    """
    cols = ["area","PV","Wind","OCGT","Storage"]
    if df.empty or "techs" not in df.columns or "cost_investment" not in df.columns:
        return pd.DataFrame(columns=cols)

    df = df.copy()
    df["techs"] = df["techs"].astype(str)
    df["area"] = df.apply(get_area_from_row, axis=1)
    df["cost_investment"] = pd.to_numeric(df["cost_investment"], errors="coerce").fillna(0.0)

    # Maschere categoria
    pv_mask   = df["techs"].str.match(PV_NEW)   & ~df["techs"].str.contains(INSTALLED_END)
    wind_mask = df["techs"].str.match(WIND_NEW) & ~df["techs"].str.contains(INSTALLED_END)
    ocgt_mask = df["techs"].eq("OCGT_NG_new")
    stor_mask = df["techs"].isin(["BESS","PHES"])  # solo esatti

    def sum_by_area(mask):
        return (df.loc[mask, ["area","cost_investment"]]
                  .groupby("area", as_index=False)["cost_investment"].sum()
                  .rename(columns={"cost_investment":"val"}))

    pv_sum   = sum_by_area(pv_mask)
    wind_sum = sum_by_area(wind_mask)
    ocgt_sum = sum_by_area(ocgt_mask)
    stor_sum = sum_by_area(stor_mask)

    out = pd.DataFrame({"area": pd.unique(
        pd.concat([pv_sum["area"], wind_sum["area"], ocgt_sum["area"], stor_sum["area"]], ignore_index=True)
    )})
    out = out.merge(pv_sum,   on="area", how="left").rename(columns={"val":"PV"})
    out = out.merge(wind_sum, on="area", how="left").rename(columns={"val":"Wind"})
    out = out.merge(ocgt_sum, on="area", how="left").rename(columns={"val":"OCGT"})
    out = out.merge(stor_sum, on="area", how="left").rename(columns={"val":"Storage"})
    out = out.fillna(0.0)

    # → B$
    for c in ["PV","Wind","OCGT","Storage"]:
        out[c] = out[c] / 1e9

    # Ordina per totale desc
    out = out.assign(Total=out[["OCGT","Wind","PV","Storage"]].sum(axis=1))
    out = out.sort_values("Total", ascending=False).reset_index(drop=True)
    return out

def collect_scenario(base_dir: Path, year: str, scen_folder: str) -> pd.DataFrame:
    """Ritorna investimenti per area per lo scenario richiesto."""
    res_dir = base_dir / "run_autarky" / scen_folder / RESULTS_SUB
    inv_path = res_dir / INV_FILE
    if not inv_path.exists():
        cand = [f for f in os.listdir(res_dir) if res_dir.exists()
                and f.lower().endswith(".csv") and "invest" in f.lower() and "cost" in f.lower()]
        if cand:
            inv_path = res_dir / cand[0]
    if not inv_path.exists():
        dprint(f"[{year}] Manca investimento: {inv_path}")
        return pd.DataFrame(columns=["area","PV","Wind","OCGT","Storage","Total"])

    df_cost = read_costs_csv(inv_path)
    return aggregate_investments_by_area(df_cost)

def save_bars_for_scenario(df: pd.DataFrame, scen: str, out_dir: Path):
    """
    Salva PNG con barre per area (stack OCGT/Wind/PV/Storage) + etichette totali.
    """
    if df.empty or df["Total"].sum() <= 0:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_axis_off()
        out = out_dir / f"{scen}_bars.png"
        plt.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"⚠️  Vuoto: {out}")
        return

    # Impaginazione
    n = len(df)
    width = min(20, max(10, n * 0.5))  # scala la larghezza secondo il numero di aree
    fig, ax = plt.subplots(figsize=(width, 6))

    x = np.arange(n)
    bottom = np.zeros(n)

    for cat in ["OCGT","Wind","PV","Storage"]:
        vals = df[cat].to_numpy()
        ax.bar(x, vals, bottom=bottom, label=cat, color=COL[cat], edgecolor="white")
        bottom += vals  # bottom → totale colonna

    # Etichette totali in B$
    totals = bottom
    y_max = float(max(1e-9, totals.max()))
    ax.set_ylim(0, y_max * 1.15)
    offset = max(y_max * 0.012, 0.005)
    for xi, val in zip(x, totals):
        if val > 0:
            ax.text(xi, val + offset, f"{val:.2f}", ha="center", va="bottom", fontsize=9, clip_on=False)

    ax.set_xticks(x, df["area"], rotation=60, ha="right", fontsize=9)
    ax.set_ylabel("Investment [B$]")
    ax.set_title(scen.replace("autarky_", ""), fontsize=12, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.margins(x=0.01)

    # Legenda
    ax.legend(loc="upper left", ncol=4, frameon=True)

    out = out_dir / f"{scen}_bars.png"
    plt.tight_layout()
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ Salvato: {out}")

# ===== MAIN =====
year = "2030"
scenarios = [
    f"autarky_VRES_{year}_nostorage",
    f"autarky_VRES_{year}_BESS",
    f"autarky_VRES_{year}_PHES",
    f"autarky_GT+VRES_{year}_nostorage",
    f"autarky_GT+VRES_{year}_BESS",
    f"autarky_GT+VRES_{year}_PHES",
]

for scen in scenarios:
    df_area = collect_scenario(BASE_2030, year, scen)
    save_bars_for_scenario(df_area, scen, OUT_DIR)
