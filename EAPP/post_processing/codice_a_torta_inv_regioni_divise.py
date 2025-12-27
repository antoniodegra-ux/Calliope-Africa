# -*- coding: utf-8 -*-
"""
Autarky 2030 — 6 PNG separati: pie distribuzione investimenti (B$) per Stato/Regione
- NON aggrega più le regioni: usa 'locs' intero (es. DRC_E) oppure il blocco paese[_regione] dal nome tech.
- Scenari: VRES/GT × N/B/P in BASE_2030/run_autarky/
- Filtri:
  * PV/Wind: SOLO ^PV_.*_MSR / ^Wind_.*_MSR, ESCLUDE *_installed
  * Storage: SOLO 'BESS' e 'PHES' (no *_installed)
  * Transmission: esclusa
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

OUT_DIR  = Path(r"C:\Users\ilari\OneDrive\Desktop\tesi\GRAFICI\INV BY COUNTRY\PIES_2030")
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEBUG = True
MIN_SHARE_LABEL = 0.01  # 1% -> voci sotto questa quota finiscono in "Other" (solo per leggibilità torta)

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
    Ritorna: area (paese o paese_regione), Total_BUSD (somma OCGT+Wind+PV+Storage in B$)
    Applica filtri: PV/Wind solo nuove build, niente *_installed; Storage solo BESS/PHES.
    """
    if df.empty or "techs" not in df.columns or "cost_investment" not in df.columns:
        return pd.DataFrame(columns=["area","Total_BUSD"])

    df = df.copy()
    df["techs"] = df["techs"].astype(str)
    df["area"] = df.apply(get_area_from_row, axis=1)
    df["cost_investment"] = pd.to_numeric(df["cost_investment"], errors="coerce").fillna(0.0)

    pv_mask   = df["techs"].str.match(PV_NEW)   & ~df["techs"].str.contains(INSTALLED_END)
    wind_mask = df["techs"].str.match(WIND_NEW) & ~df["techs"].str.contains(INSTALLED_END)
    ocgt_mask = df["techs"].eq("OCGT_NG_new")
    stor_mask = df["techs"].isin(["BESS","PHES"])

    use_mask = pv_mask | wind_mask | ocgt_mask | stor_mask
    sub = df.loc[use_mask, ["area","cost_investment"]].copy()

    tot = (sub.groupby("area", as_index=False)["cost_investment"].sum()
             .rename(columns={"cost_investment":"Total_BUSD"}))
    tot["Total_BUSD"] = tot["Total_BUSD"] / 1e9  # → B$
    tot = tot.sort_values("Total_BUSD", ascending=False).reset_index(drop=True)
    return tot

def collect_scenario_totals(base_dir: Path, year: str, scen_folder: str) -> pd.DataFrame:
    res_dir = base_dir / "run_autarky" / scen_folder / RESULTS_SUB
    inv_path = res_dir / INV_FILE
    if not inv_path.exists():
        cand = [f for f in os.listdir(res_dir) if res_dir.exists()
                and f.lower().endswith(".csv") and "invest" in f.lower() and "cost" in f.lower()]
        if cand:
            inv_path = res_dir / cand[0]
    if not inv_path.exists():
        dprint(f"[{year}] Manca investimento: {inv_path}")
        return pd.DataFrame(columns=["area","Total_BUSD"])

    df_cost = read_costs_csv(inv_path)
    return aggregate_investments_by_area(df_cost)

def build_color_map(dict_dfs: dict) -> dict:
    """Colori coerenti per area su tutti gli scenari (tab20 ciclico)."""
    all_areas = sorted(set(
        a for df in dict_dfs.values() for a in (df["area"].tolist() if not df.empty else [])
    ))
    palette = plt.cm.tab20(np.linspace(0, 1, 20))
    return {a: palette[i % 20] for i, a in enumerate(all_areas)} | {"Other": (0.85,0.85,0.85,1.0)}

def save_pie_for_scenario(df: pd.DataFrame, scen: str, color_map: dict, out_dir: Path):
    if df.empty or df["Total_BUSD"].sum() <= 0:
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_axis_off()
        out = out_dir / f"{scen}_pie.png"
        plt.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"⚠️  Vuoto: {out}")
        return

    total = df["Total_BUSD"].sum()
    d = df.copy()
    d["share"] = d["Total_BUSD"] / total

    major = d[d["share"] >= MIN_SHARE_LABEL].copy()
    minor = d[d["share"] <  MIN_SHARE_LABEL].copy()
    if not minor.empty:
        other_val = minor["Total_BUSD"].sum()
        major = pd.concat([major, pd.DataFrame([{"area":"Other","Total_BUSD":other_val,"share":other_val/total}])],
                          ignore_index=True)
    major = major.sort_values("Total_BUSD", ascending=False)

    labels = major["area"].tolist()
    sizes  = major["Total_BUSD"].to_numpy()
    colors = [color_map.get(a, color_map["Other"]) for a in labels]

    fig, ax = plt.subplots(figsize=(7, 6))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=None,
        autopct=lambda p: f"{p:.1f}%" if p >= MIN_SHARE_LABEL*100 else "",
        startangle=90,
        colors=colors,
        pctdistance=0.75,
        textprops=dict(color="black", fontsize=10),
        wedgeprops=dict(linewidth=0.8, edgecolor="white")
    )
    ax.axis('equal')
    ax.set_title(scen.replace("autarky_", ""), fontsize=12, fontweight="bold")
    ax.text(0.5, -0.08, f"Total: {total:.2f} B$", transform=ax.transAxes, ha="center", va="top", fontsize=10)

    # legenda a destra
    ax.legend(wedges, labels, title="Area", loc="center left",
              bbox_to_anchor=(1.02, 0.5), fontsize=9, frameon=True)

    out = out_dir / f"{scen}_pie.png"
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

data = {scen: collect_scenario_totals(BASE_2030, year, scen) for scen in scenarios}
cm = build_color_map(data)

for scen in scenarios:
    save_pie_for_scenario(data[scen], scen, cm, OUT_DIR)
