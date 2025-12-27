# -*- coding: utf-8 -*-
"""
Investimenti per PAESE (B$) - Autarky 2030
- Scansiona 6 scenari standard in BASE_2030/run_autarky/
- Legge results_cost_investment.csv (costs == 'monetary')
- Aggrega investimenti per PAESE e CATEGORIA (PV, Wind, OCGT, Storage)
  * PV/Wind: SOLO ^PV_.*_MSR / ^Wind_.*_MSR e NON *_installed
  * Storage: SOLO 'BESS' e 'PHES' (esclude qualunque *_installed)
  * Transmission esclusa
- Grafico: 6 subplot (uno per scenario), barre impilate per PAESE, con etichette valore totale
- Salva anche CSV di dettaglio
"""

from pathlib import Path
import os, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ========== CONFIG ==========
BASE_2030 = Path(r"C:\Users\ilari\OneDrive\Desktop\tesi\2040_true\run_2040_new_true")
RESULTS_SUB = Path("results")
INV_FILE = "results_cost_investment.csv"

OUT_DIR  = Path(r"C:\Users\ilari\OneDrive\Desktop\tesi\GRAFICI\INV BY COUNTRY")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FIG = OUT_DIR / "Investment_byCountry_2040_autarky.png"
OUT_CSV = OUT_DIR / "Investment_byCountry_2040_autarky.csv"

DEBUG = True

# Colori (coerenti con i tuoi grafici)
COL = {"OCGT":"#f4b6b6", "Wind":"#cfe3ff", "PV":"#ffd34d", "Storage":"#b9d97c"}

def dprint(*a):
    if DEBUG: print(*a)

# Pattern per NUOVE build e per esclusione installed
PV_NEW        = re.compile(r"^PV_.*_MSR",   re.IGNORECASE)
WIND_NEW      = re.compile(r"^Wind_.*_MSR", re.IGNORECASE)
INSTALLED_END = re.compile(r"_installed$",  re.IGNORECASE)

# Estrazione paese da 'techs' e/o 'locs'
TECH_COUNTRY = re.compile(r"^(PV|Wind)_([A-Za-z0-9]+)_", re.IGNORECASE)

def read_costs_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "costs" in df.columns:
        df = df[df["costs"].astype(str).str.lower().eq("monetary")]
    return df

def get_country_from_row(row) -> str:
    """Ordine di priorità: locs -> techs (PV_/Wind_) -> 'UNK'."""
    # 1) locs
    loc = str(row.get("locs", "")).strip()
    if loc and loc.lower() != "nan":
        # prendo il token prima di '_' se presente (es. 'DRC_E' -> 'DRC')
        tok = loc.split("_")[0]
        if tok:
            return tok.upper()
    # 2) techs
    tech = str(row.get("techs", "")).strip()
    m = TECH_COUNTRY.match(tech)
    if m:
        return m.group(2).upper()
    # 3) fallback
    return "UNK"

def aggregate_investments_by_country(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ritorna DataFrame con colonne: country, PV, Wind, OCGT, Storage (valori in B$).
    Applica filtri: PV/Wind solo nuove build, niente *_installed; Storage solo BESS/PHES.
    """
    cols = ["country","PV","Wind","OCGT","Storage"]
    if df.empty or "techs" not in df.columns or "cost_investment" not in df.columns:
        return pd.DataFrame(columns=cols)

    df = df.copy()
    df["techs"] = df["techs"].astype(str)
    df["country"] = df.apply(get_country_from_row, axis=1)
    df["cost_investment"] = pd.to_numeric(df["cost_investment"], errors="coerce").fillna(0.0)

    # Maschere categoria
    pv_mask   = df["techs"].str.match(PV_NEW)   & ~df["techs"].str.contains(INSTALLED_END)
    wind_mask = df["techs"].str.match(WIND_NEW) & ~df["techs"].str.contains(INSTALLED_END)
    ocgt_mask = df["techs"].eq("OCGT_NG_new")
    stor_mask = df["techs"].isin(["BESS","PHES"])  # solo esatti

    # Costruisco sub-dataframe per ogni categoria
    def sum_by_country(mask):
        return (df.loc[mask, ["country","cost_investment"]]
                  .groupby("country", as_index=False)["cost_investment"].sum()
                  .rename(columns={"cost_investment":"val"}))

    pv_sum   = sum_by_country(pv_mask)
    wind_sum = sum_by_country(wind_mask)
    ocgt_sum = sum_by_country(ocgt_mask)
    stor_sum = sum_by_country(stor_mask)

    # Merge outer su tutti i paesi coinvolti
    out = pd.DataFrame({"country": pd.unique(
        pd.concat([pv_sum["country"], wind_sum["country"], ocgt_sum["country"], stor_sum["country"]], ignore_index=True)
    )})
    out = out.merge(pv_sum,   on="country", how="left").rename(columns={"val":"PV"})
    out = out.merge(wind_sum, on="country", how="left").rename(columns={"val":"Wind"})
    out = out.merge(ocgt_sum, on="country", how="left").rename(columns={"val":"OCGT"})
    out = out.merge(stor_sum, on="country", how="left").rename(columns={"val":"Storage"})
    out = out.fillna(0.0)

    # → B$ (divider per 1e9)
    for c in ["PV","Wind","OCGT","Storage"]:
        out[c] = out[c] / 1e9

    # Ordina paesi alfabeticamente
    out = out.sort_values("country").reset_index(drop=True)
    return out

def collect_scenario(base_dir: Path, year: str, scen_folder: str) -> pd.DataFrame:
    """Ritorna investimenti per paese per lo scenario richiesto, con colonna 'scenario'."""
    res_dir = base_dir / "run_autarky" / scen_folder / RESULTS_SUB
    inv_path = res_dir / INV_FILE
    if not inv_path.exists():
        cand = [f for f in os.listdir(res_dir) if res_dir.exists()
                and f.lower().endswith(".csv") and "invest" in f.lower() and "cost" in f.lower()]
        if cand:
            inv_path = res_dir / cand[0]
    if not inv_path.exists():
        dprint(f"[{year}] Manca investimento: {inv_path}")
        return pd.DataFrame(columns=["scenario","country","PV","Wind","OCGT","Storage"])

    df_cost = read_costs_csv(inv_path)
    agg = aggregate_investments_by_country(df_cost)
    agg.insert(0, "scenario", scen_folder)
    return agg

def collect_all_2030(base_2030: Path) -> dict[str, pd.DataFrame]:
    """Raccoglie i 6 scenari standard 2030 e ritorna un dizionario {scenario: df_by_country}."""
    year = "2040"
    scen_list = [
        f"autarky_VRES_{year}_nostorage",
        f"autarky_VRES_{year}_BESS",
        f"autarky_VRES_{year}_PHES",
        f"autarky_GT+VRES_{year}_nostorage",
        f"autarky_GT+VRES_{year}_BESS",
        f"autarky_GT+VRES_{year}_PHES",
    ]
    out = {}
    for scen in scen_list:
        out[scen] = collect_scenario(base_2030, year, scen)
    return out

# ===== MAIN =====
data_by_scen = collect_all_2030(BASE_2030)

# CSV complessivo
detail_rows = []
for scen, dfc in data_by_scen.items():
    if not dfc.empty:
        detail_rows.append(dfc)
if detail_rows:
    detail_df = pd.concat(detail_rows, ignore_index=True)
else:
    detail_df = pd.DataFrame(columns=["scenario","country","PV","Wind","OCGT","Storage"])
detail_df.to_csv(OUT_CSV, index=False)
dprint(f"[SALVATO CSV] {OUT_CSV}")

# ===== PLOT (6 subplot, uno per scenario) =====
scenarios_order = [
    f"autarky_VRES_2040_nostorage",
    f"autarky_VRES_2040_BESS",
    f"autarky_VRES_2040_PHES",
    f"autarky_GT+VRES_2040_nostorage",
    f"autarky_GT+VRES_2040_BESS",
    f"autarky_GT+VRES_2040_PHES",
]

fig, axes = plt.subplots(2, 3, figsize=(16, 8), sharey=True)
axes = axes.flat

for ax, scen in zip(axes, scenarios_order):
    dfc = data_by_scen.get(scen, pd.DataFrame())
    if dfc.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_axis_off()
        continue

    # Ordina paesi per totale investimenti
    dfc = dfc.assign(Total=dfc[["OCGT","Wind","PV","Storage"]].sum(axis=1)).sort_values("Total", ascending=False)

    x = np.arange(len(dfc))
    bottom = np.zeros(len(dfc))

    # Stack
    for cat in ["OCGT","Wind","PV","Storage"]:
        vals = dfc[cat].to_numpy()
        ax.bar(x, vals, bottom=bottom, label=cat, color=COL[cat], edgecolor="white")
        bottom += vals  # alla fine = totale colonna

    # --- Etichette valore totale sopra ogni colonna (anche se piccola) ---
    totals = bottom  # B$
    y_max = max(1e-9, float(totals.max()))
    ax.set_ylim(0, y_max * 1.15)  # spazio per le etichette

    # offset verticale: proporzionale, con minimo per barre piccole
    offset = max(y_max * 0.012, 0.005)  # B$
    for xi, val in zip(x, totals):
        if val > 0:
            ax.text(
                xi, val + offset, f"{val:.2f}", ha="center", va="bottom",
                fontsize=9, rotation=0, clip_on=False
            )

    ax.set_xticks(x, dfc["country"], rotation=45, ha="right", fontsize=9)
    ax.set_title(scen.replace("autarky_",""), fontsize=11)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.margins(x=0.02)

# Y label comune
axes[0].set_ylabel("Investment [B$]")
axes[3].set_ylabel("Investment [B$]")

# Legenda unica
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=4, frameon=True)

fig.suptitle("Autarky 2030 — Investment by Country (B$)", fontsize=18, fontweight="bold", y=0.98)
plt.tight_layout(rect=[0,0,1,0.93])
plt.savefig(OUT_FIG, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"✅ Figura salvata: {OUT_FIG}")
