# -*- coding: utf-8 -*-
"""
existing: Investment Costs (B$) per 2030, 2035, 2040 con CSV diagnostici.
- Struttura cartelle:
    BASE_20xx/run_existing/existing_VRES_20xx_{nostorage|BESS|PHES}
    BASE_20xx/run_existing/existing_GT+VRES_20xx_{nostorage|BESS|PHES}
- Stack categorie: OCGT, Wind, PV, Storage (BESS+PHES) + LCOE come pallini rossi.
- PV/Wind: SOLO nuove build (^PV_.*_MSR / ^Wind_.*_MSR), ESCLUDE *_installed.
- Storage: SOLO tech == 'BESS' o 'PHES' (esclude qualunque *_installed).
"""

from pathlib import Path
import os, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ========= CONFIG =========
BASE_2030 = Path("/Users/antoniodegrazia/Desktop/run_2030_new_true")
BASE_2035 = Path("/Users/antoniodegrazia/Desktop/run_2035_new_true")
BASE_2040 = Path("/Users/antoniodegrazia/Desktop/run_2040_new_true")  # <-- aggiorna se serve

OUT_DIR   = Path("/Users/antoniodegrazia/Desktop/planning/grafici/INVESTIMENTO GRAFICO")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUTFIG        = OUT_DIR / "existing_Investment_2030_2035_2040.png"
OUT_CSV_DETAIL= OUT_DIR / "Investment_detail_2030_2035_2040.csv"
OUT_CSV_DELTA_35_30 = OUT_DIR / "Investment_delta_2035_vs_2030.csv"
OUT_CSV_DELTA_40_35 = OUT_DIR / "Investment_delta_2040_vs_2035.csv"
OUT_CSV_DELTA_40_30 = OUT_DIR / "Investment_delta_2040_vs_2030.csv"

RESULTS_SUB = Path("results")
INV_FILE  = "results_cost_investment.csv"
LCOE_FILE = "results_total_levelised_cost.csv"
DEBUG = True

# Colori (come screenshot)
COL = {"OCGT":"#f4b6b6", "Wind":"#cfe3ff", "PV":"#ffd34d", "Storage":"#b9d97c"}
LCOE_COLOR = "red"

def dprint(*a):
    if DEBUG: print(*a)

# --- filtri per PV/Wind "solo nuovi" ed esclusione installed ---
PV_NEW        = re.compile(r"^PV_.*_MSR",   re.IGNORECASE)
WIND_NEW      = re.compile(r"^Wind_.*_MSR", re.IGNORECASE)
INSTALLED_END = re.compile(r"_installed$",  re.IGNORECASE)

def read_costs_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "costs" in df.columns:
        df = df[df["costs"].astype(str).str.lower().eq("monetary")]
    return df

def read_lcoe(results_dir: Path) -> float:
    """LCOE in $/MWh (se è $/kWh → ×1000)."""
    p = results_dir / LCOE_FILE
    if not p.exists(): return np.nan
    df = read_costs_csv(p)
    if df.empty: return np.nan
    if "value" in df.columns:
        s = pd.to_numeric(df["value"], errors="coerce")
    else:
        num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not num:
            conv = df.apply(pd.to_numeric, errors="coerce")
            num = [c for c in conv.columns if np.isfinite(conv[c]).any()]
            if not num: return np.nan
            s = conv[num[0]]
        else:
            s = df[num[0]]
    s = s.replace([np.inf,-np.inf], np.nan).dropna()
    if s.empty: return np.nan
    v = float(s.iloc[0])
    return v*1000.0 if v < 10 else v

def group_investments_BUSD(df: pd.DataFrame) -> pd.Series:
    """
    Aggrega investimenti (B$):
      - PV:   SOLO ^PV_.*_MSR e NON *_installed
      - Wind: SOLO ^Wind_.*_MSR e NON *_installed
      - OCGT: OCGT_NG_new
      - Storage: SOLO 'BESS' + 'PHES' (esclude *_installed o varianti)
    """
    out = {"PV":0.0, "Wind":0.0, "OCGT":0.0, "Storage":0.0}
    if df.empty or "techs" not in df.columns or "cost_investment" not in df.columns:
        return pd.Series(out)

    tech = df["techs"].astype(str)
    cost = pd.to_numeric(df["cost_investment"], errors="coerce").fillna(0.0)

    pv_mask   = tech.str.match(PV_NEW)   & ~tech.str.contains(INSTALLED_END)
    wind_mask = tech.str.match(WIND_NEW) & ~tech.str.contains(INSTALLED_END)
    ocgt_mask = tech.eq("OCGT_NG_new")
    stor_mask = tech.isin(["BESS","PHES"])

    pv   = float(cost[pv_mask].sum())
    wind = float(cost[wind_mask].sum())
    ocgt = float(cost[ocgt_mask].sum())
    stor = float(cost[stor_mask].sum())

    return pd.Series({"PV":pv, "Wind":wind, "OCGT":ocgt, "Storage":stor}) / 1e9  # → B$

def parse_group_storage(folder: str) -> tuple[str,str]:
    n = folder.lower()
    group = "VRES+GT" if "+vres" in n else "VRES"
    if   "nostorage" in n or "no_storage" in n: code = "N"
    elif "bess" in n: code = "B"
    elif "phes" in n: code = "P"
    else: code = "?"
    return group, code

def collect_year(base_dir: Path, year: str) -> pd.DataFrame:
    """Ritorna df ordinato: group, code, PV, Wind, OCGT, Storage, LCOE (B$ e $/MWh)."""
    run_dir = base_dir / "run_existing"
    wanted = [
        f"existing_VRES_{year}_nostorage",
        f"existing_VRES_{year}_BESS",
        f"existing_VRES_{year}_PHES",
        f"existing_GT+VRES_{year}_nostorage",
        f"existing_GT+VRES_{year}_BESS",
        f"existing_GT+VRES_{year}_PHES",
    ]

    rows = []
    for scen in wanted:
        res_dir = run_dir / scen / RESULTS_SUB
        inv_path = res_dir / INV_FILE
        if not inv_path.exists():
            cand = [f for f in os.listdir(res_dir) if res_dir.exists() and f.lower().endswith(".csv")
                    and "invest" in f.lower() and "cost" in f.lower()]
            if cand:
                inv_path = res_dir / cand[0]

        if inv_path.exists():
            df_cost = read_costs_csv(inv_path)
        else:
            dprint(f"[{year}] Manca investimento: {inv_path}")
            df_cost = pd.DataFrame(columns=["techs","cost_investment","costs"])

        sums = group_investments_BUSD(df_cost)
        group, code = parse_group_storage(scen)
        lcoe = read_lcoe(res_dir)

        rows.append({"scenario": scen, "group": group, "code": code,
                     "PV":sums["PV"], "Wind":sums["Wind"], "OCGT":sums["OCGT"], "Storage":sums["Storage"],
                     "LCOE": lcoe})

    df = pd.DataFrame(rows)

    # Ordine: VRES [N,B,P] → VRES+GT [N,B,P]
    order = []
    for g in ["VRES","VRES+GT"]:
        for c in ["N","B","P"]:
            mask = (df["group"]==g) & (df["code"]==c)
            if mask.any():
                order.extend(df.index[mask].tolist())
    return df.loc[order].reset_index(drop=True)

# ======== MAIN ========
df30 = collect_year(BASE_2030, "2030")
df35 = collect_year(BASE_2035, "2035")
df40 = collect_year(BASE_2040, "2040")

# ----- CSV dettaglio -----
detail = (pd.concat([
            df30.assign(year="2030"),
            df35.assign(year="2035"),
            df40.assign(year="2040"),
         ], ignore_index=True)
         [["year","group","code","PV","Wind","OCGT","Storage","LCOE","scenario"]])
detail.to_csv(OUT_CSV_DETAIL, index=False)

# ----- CSV delta -----
def to_keydf(df, year):
    d = df.copy()
    d["key"] = list(zip(d["group"], d["code"]))
    cols = ["PV","Wind","OCGT","Storage","LCOE"]
    d = d[["key"] + cols]
    d.columns = ["key"] + [f"{c}_{year}" for c in cols]
    return d

def save_delta(df_old, y_old, df_new, y_new, outfile):
    delta = pd.merge(to_keydf(df_old, y_old), to_keydf(df_new, y_new), on="key", how="outer").fillna(0.0)
    for c in ["PV","Wind","OCGT","Storage","LCOE"]:
        delta[f"Δ{c}_{y_new}-{y_old}"] = delta[f"{c}_{y_new}"] - delta[f"{c}_{y_old}"]
    delta.to_csv(outfile, index=False)

save_delta(df30,"2030", df35,"2035", OUT_CSV_DELTA_35_30)
save_delta(df35,"2035", df40,"2040", OUT_CSV_DELTA_40_35)
save_delta(df30,"2030", df40,"2040", OUT_CSV_DELTA_40_30)

# ----- Grafico (3 subplot) -----
fig, axes = plt.subplots(1, 3, figsize=(18, 5.2), sharey=True)

for ax, (year, data) in zip(axes, [("2030", df30), ("2035", df35), ("2040", df40)]):

    x = np.arange(len(data))
    bottom = np.zeros(len(data))

    # Stack categorie
    for cat in ["OCGT","Wind","PV","Storage"]:
        vals = data[cat].fillna(0).to_numpy()
        ax.bar(x, vals, bottom=bottom, label=cat, color=COL[cat], edgecolor="white")
        bottom += vals

    # Ticks & label anno
    ax.set_xticks(x, data["code"])
    ax.set_xlabel(year)
    ax.set_ylabel("Investment [B$]" if year == "2030" else "")

    # Scritte VRES / VRES+GT in alto
    for g in ["VRES","VRES+GT"]:
        idxs = [i for i,(G,C) in enumerate(zip(data["group"], data["code"])) if G==g]
        if idxs:
            mid = (idxs[0] + idxs[-1]) / 2
            ymax = max(1e-9, ax.get_ylim()[1])
            ax.text(mid, ymax*1.02, g, ha="center", va="bottom", fontsize=11, fontweight="bold")

    # Asse destro con LCOE (pallini rossi)
    ax2 = ax.twinx()
    ax2.yaxis.set_label_position("right")
    ax2.yaxis.tick_right()
    ax2.set_ylabel("LCOE [$/MWh]")
    ax2.plot(x, data["LCOE"].to_numpy(), linestyle="none", marker="o",
             markersize=5, color=LCOE_COLOR, label="LCOE", zorder=5)

    # Legenda combinata (solo sul primo subplot)
    if year == "2030":
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax2.legend(h1+h2, l1+l2, loc="upper left", frameon=True)

    # Box N/B/P
    ax.text(0.63, 0.78, "N = NoStorage\nB = BESS\nP = PHES",
            transform=ax.transAxes, fontsize=9,
            bbox=dict(facecolor="white", edgecolor="0.7", boxstyle="round,pad=0.3"))

    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.margins(x=0.06)

fig.suptitle("existing: Investment Costs B$ (2030–2035–2040)", fontsize=18, fontweight="bold", y=0.98)
plt.tight_layout(rect=[0,0,1,0.95])
plt.savefig(OUTFIG, dpi=300, bbox_inches="tight")
plt.close(fig)

print(f"✅ Figura salvata: {OUTFIG}")
print(f"✅ CSV dettaglio: {OUT_CSV_DETAIL}")
print(f"✅ CSV delta 35-30: {OUT_CSV_DELTA_35_30}")
print(f"✅ CSV delta 40-35: {OUT_CSV_DELTA_40_35}")
print(f"✅ CSV delta 40-30: {OUT_CSV_DELTA_40_30}")
