# -*- coding: utf-8 -*-
"""
new_trasmission: % VRES (PV/Wind) per 2030, 2035, 2040, con doppia metrica:
- % su PRODUZIONE TOTALE (no storage/trasmissione/spurie)  -> 'vres_share_total_pct'
- % su SOLE RINNOVABILI (PV+Wind+Hydro+Geo+Bio)            -> 'vres_share_ren_pct'

Salva:
  - 2 grafici sulla metrica "su totale":
      * singleplot con 2030-2035-2040 (triplette per cella)
      * 3 subplot (2030 | 2035 | 2040)
  - CSV dettaglio con entrambe le metriche per tutti gli anni
  - 3 CSV delta:
      * Δ 2035 vs 2030
      * Δ 2040 vs 2035
      * Δ 2040 vs 2030
"""

from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ===== CONFIG =====
BASE_2030 = Path("/Users/antoniodegrazia/Desktop/run_2030_new_true")
BASE_2035 = Path("/Users/antoniodegrazia/Desktop/run_2035_new_true")
BASE_2040 = Path("/Users/antoniodegrazia/Desktop/run_2040_new_true")  # <--- aggiorna se diverso

OUT_DIR       = Path("/Users/antoniodegrazia/Desktop/VRES_grafico")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_COMBINED  = OUT_DIR / "VRES_share_2030_2035_2040_singleplot.png"
OUT_SPLIT     = OUT_DIR / "VRES_share_2030_2035_2040_subplot.png"
OUT_CSV       = OUT_DIR / "VRES_share_detail.csv"
OUT_DELTA_35_30 = OUT_DIR / "VRES_share_delta_2035_vs_2030.csv"
OUT_DELTA_40_35 = OUT_DIR / "VRES_share_delta_2040_vs_2035.csv"
OUT_DELTA_40_30 = OUT_DIR / "VRES_share_delta_2040_vs_2030.csv"

RESULTS_REL = Path("results") / "results_carrier_prod.csv"
DEBUG = True

# colori
WIND_30 = "#c7d4e2"; PV_30 = "#ffe08a"
WIND_35 = "#93b2d0"; PV_35 = "#ffd966"
WIND_40 = "#5e8fb9"; PV_40 = "#ffcb52"

# === PATTERN ===
# Escludi dallo "totale pulito" storage, TUTTE le trasmissioni (anche con :DEST), e voci spurie
EXCLUDE_TOTAL_PATTERN = re.compile(
    r"(?:(?:BESS|PHES)|"                       # storage
    r"^(?:\d{3})_kV(?::|$)|"                  # 132/220/400/500_kV con o senza ':DEST'
    r"^transmission_2030_installed(?::|$)|"
    r"^transmission(?::|$)|"
    r"^HVDC|"
    r"^new_transmission(?::|$)|^new_trasmission(?::|$)|"  # typo incluso
    r"(?:curtail|dump|excess|unmet|shed))",               # non-produzione utile
    re.IGNORECASE
)

# Pattern PV/Wind robusti
PV_PATTERN   = re.compile(r"(?:\bPV\b|\bSolar\b|\bPhotovoltaic\b|SolarPV)", re.IGNORECASE)
WIND_PATTERN = re.compile(r"\bWind\b", re.IGNORECASE)

# Pattern altre rinnovabili per il denominatore "solo rinnovabili"
REN_EXTRA_PATTERN = re.compile(
    r"(?:\bHydro(?:power|electric)?\b|\bGeo(?:thermal)?\b|\bBio(?:mass|energy)?\b)",
    re.IGNORECASE
)

def dprint(*a):
    if DEBUG:
        print(*a)

def robust_read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path).dropna(how="all")
    return df

def pick_tech_col(df: pd.DataFrame) -> str:
    for c in ["tech","techs","Technology","technology","Tech","name"]:
        if c in df.columns:
            return c
    return df.columns[0]

def get_value_series(df: pd.DataFrame):
    tech_col = pick_tech_col(df)

    # Se c'è carrier_prod numerico: somma e azzera i negativi (export/carichi)
    if "carrier_prod" in df.columns and pd.api.types.is_numeric_dtype(df["carrier_prod"]):
        df = df.copy()
        df.loc[df["carrier_prod"] < 0, "carrier_prod"] = 0.0
        tmp = df.groupby(tech_col, dropna=False)["carrier_prod"].sum().reset_index()
        return tmp[tech_col].astype(str), tmp["carrier_prod"]

    # fallback: somma tutte le numeriche
    num = df.select_dtypes(include="number")
    if num.empty:
        raise ValueError("Nessuna colonna numerica trovata.")
    df2 = df[[tech_col]].copy()
    df2["_val"] = num.sum(axis=1)
    tmp = df2.groupby(tech_col, dropna=False)["_val"].sum().reset_index()
    return tmp[tech_col].astype(str), tmp["_val"]

def compute_shares(csv_path: Path):
    """
    Ritorna:
      pv_pct_total, wind_pct_total, pv_val, wind_val, tot_total,
      pv_pct_ren,   wind_pct_ren,   tot_ren
    (tutte le quantità *_val e tot_* sono in kWh)
    """
    df = robust_read_csv(csv_path)

    # (facoltativo ma sicuro) se c'è 'carriers', tieni solo electricity
    if "carriers" in df.columns:
        df = df[df["carriers"].astype(str).str.lower() == "electricity"]

    techs, vals = get_value_series(df)

    # Maschere
    pv_mask   = techs.str.contains(PV_PATTERN,   na=False) | techs.str.contains("_PV",   case=False, na=False)
    wind_mask = techs.str.contains(WIND_PATTERN, na=False) | techs.str.contains("Wind_", case=False, na=False)

    pv_val   = float(vals[pv_mask].sum())
    wind_val = float(vals[wind_mask].sum())

    # Denominatore "totale produzione" (no storage/trasmissione/spurie)
    excl_mask = techs.str.contains(EXCLUDE_TOTAL_PATTERN, na=False)
    tot_total = float(vals[~excl_mask].sum())

    # Denominatore "solo rinnovabili"
    ren_extra_mask = techs.str.contains(REN_EXTRA_PATTERN, na=False)
    ren_mask = (pv_mask | wind_mask | ren_extra_mask) & (~excl_mask)
    tot_ren  = float(vals[ren_mask].sum())

    # Percentuali
    if tot_total > 0:
        pv_pct_total   = 100.0 * pv_val   / tot_total
        wind_pct_total = 100.0 * wind_val / tot_total
    else:
        pv_pct_total = wind_pct_total = 0.0

    if tot_ren > 0:
        pv_pct_ren   = 100.0 * pv_val   / tot_ren
        wind_pct_ren = 100.0 * wind_val / tot_ren
    else:
        pv_pct_ren = wind_pct_ren = 0.0

    return (
        pv_pct_total, wind_pct_total, pv_val, wind_val, tot_total,
        pv_pct_ren,   wind_pct_ren,   tot_ren
    )

def scen_path(base: Path, folder: str) -> Path:
    return base / "run_existing" / folder / RESULTS_REL

def build_data(base: Path, year: str):
    """Calcola metriche per le 6 celle (group, storage) nell'anno indicato."""
    scen = {
        ("VRES","N"): f"existing_VRES_{year}_nostorage",
        ("VRES","B"): f"existing_VRES_{year}_BESS",
        ("VRES","P"): f"existing_VRES_{year}_PHES",
        ("VRES+GT","N"): f"existing_GT+VRES_{year}_nostorage",
        ("VRES+GT","B"): f"existing_GT+VRES_{year}_BESS",
        ("VRES+GT","P"): f"existing_GT+VRES_{year}_PHES",
    }
    data = {}
    rows = []  # per CSV dettagli
    for (g, s), folder in scen.items():
        path = scen_path(base, folder)
        if path.exists():
            (pv_pct_tot, wind_pct_tot, pv_val, wind_val, tot_total,
             pv_pct_ren, wind_pct_ren, tot_ren) = compute_shares(path)
            vres_val = pv_val + wind_val
            dprint(
                f"[{year}] {folder}: "
                f"PV={pv_pct_tot:.1f}%, Wind={wind_pct_tot:.1f}% | "
                f"PV+W={vres_val/1e6:.2f} GWh, Tot={tot_total/1e6:.2f} GWh | "
                f"(solo REN: VRES={(pv_pct_ren+wind_pct_ren):.1f}%)"
            )
        else:
            dprint(f"[WARN] mancante: {path}")
            pv_pct_tot = wind_pct_tot = pv_pct_ren = wind_pct_ren = 0.0
            pv_val = wind_val = vres_val = tot_total = tot_ren = 0.0

        data[(g, s)] = {
            # metrica su totale (per i grafici)
            "pv_pct_tot": pv_pct_tot, "wind_pct_tot": wind_pct_tot,
            # metrica su sole rinnovabili (per CSV/diagnosi)
            "pv_pct_ren": pv_pct_ren, "wind_pct_ren": wind_pct_ren,
            # assoluti
            "pv_val": pv_val, "wind_val": wind_val,
            "vres_val": vres_val,
            "tot_total": tot_total, "tot_ren": tot_ren
        }

        rows.append({
            "year": year, "group": g, "storage": s, "scenario_folder": folder,
            # % su totale
            "PV_pct_total": pv_pct_tot, "Wind_pct_total": wind_pct_tot,
            "VRES_pct_total": pv_pct_tot + wind_pct_tot,
            # % su rinnovabili
            "PV_pct_ren": pv_pct_ren, "Wind_pct_ren": wind_pct_ren,
            "VRES_pct_ren": pv_pct_ren + wind_pct_ren,
            # assoluti (kWh)
            "PV_val_kWh": pv_val, "Wind_val_kWh": wind_val,
            "VRES_val_kWh": vres_val,
            "Total_clean_kWh": tot_total,      # denominatore "su totale"
            "Total_renewables_kWh": tot_ren    # denominatore "su sole rinnovabili"
        })
    return data, pd.DataFrame(rows)

# === CALCOLO + CSV DETTAGLIO ===
data2030, df30 = build_data(BASE_2030, "2030")
data2035, df35 = build_data(BASE_2035, "2035")
data2040, df40 = build_data(BASE_2040, "2040")
detail_df = pd.concat([df30, df35, df40], ignore_index=True)
detail_df.to_csv(OUT_CSV, index=False)
dprint(f"[SALVATO] {OUT_CSV}")

# === CSV DELTA: helper generico =============================================
def extract_for_year_df(detail_df: pd.DataFrame, year: str) -> pd.DataFrame:
    d = detail_df[detail_df["year"] == year].copy()
    d = d[[
        "group","storage",
        "PV_pct_total","Wind_pct_total","VRES_pct_total",
        "PV_pct_ren","Wind_pct_ren","VRES_pct_ren",
        "VRES_val_kWh","Total_clean_kWh","Total_renewables_kWh"
    ]]
    d = d.rename(columns={
        "PV_pct_total": f"PV_pct_total_{year}",
        "Wind_pct_total": f"Wind_pct_total_{year}",
        "VRES_pct_total": f"VRES_pct_total_{year}",
        "PV_pct_ren": f"PV_pct_ren_{year}",
        "Wind_pct_ren": f"Wind_pct_ren_{year}",
        "VRES_pct_ren": f"VRES_pct_ren_{year}",
        "VRES_val_kWh": f"VRES_kWh_{year}",
        "Total_clean_kWh": f"Total_kWh_{year}",
        "Total_renewables_kWh": f"TotalREN_kWh_{year}",
    })
    return d

def rel_pct(new_val: pd.Series, old_val: pd.Series):
    den = old_val.astype(float)
    num = new_val.astype(float) - den
    out = np.where(den != 0, 100.0 * num / den, np.nan)  # np.nan se base è 0
    return out

def make_delta(detail_df: pd.DataFrame, y_new: str, y_old: str, outfile: Path):
    d_old = extract_for_year_df(detail_df, y_old)
    d_new = extract_for_year_df(detail_df, y_new)
    delta = pd.merge(d_old, d_new, on=["group","storage"], how="outer").fillna(0.0)

    # Δ percentuali (assolute)
    delta[f"ΔPV_pct_total_{y_new}-{y_old}"]   = delta[f"PV_pct_total_{y_new}"]   - delta[f"PV_pct_total_{y_old}"]
    delta[f"ΔWind_pct_total_{y_new}-{y_old}"] = delta[f"Wind_pct_total_{y_new}"] - delta[f"Wind_pct_total_{y_old}"]
    delta[f"ΔVRES_pct_total_{y_new}-{y_old}"] = delta[f"VRES_pct_total_{y_new}"] - delta[f"VRES_pct_total_{y_old}"]

    delta[f"ΔPV_pct_ren_{y_new}-{y_old}"]   = delta[f"PV_pct_ren_{y_new}"]   - delta[f"PV_pct_ren_{y_old}"]
    delta[f"ΔWind_pct_ren_{y_new}-{y_old}"] = delta[f"Wind_pct_ren_{y_new}"] - delta[f"Wind_pct_ren_{y_old}"]
    delta[f"ΔVRES_pct_ren_{y_new}-{y_old}"] = delta[f"VRES_pct_ren_{y_new}"] - delta[f"VRES_pct_ren_{y_old}"]

    # Δ volumi
    delta[f"ΔVRES_kWh_{y_new}-{y_old}"]   = delta[f"VRES_kWh_{y_new}"]   - delta[f"VRES_kWh_{y_old}"]
    delta[f"ΔTotal_kWh_{y_new}-{y_old}"]  = delta[f"Total_kWh_{y_new}"]  - delta[f"Total_kWh_{y_old}"]
    delta[f"ΔTotalREN_kWh_{y_new}-{y_old}"] = delta[f"TotalREN_kWh_{y_new}"] - delta[f"TotalREN_kWh_{y_old}"]

    # % relative
    delta[f"ΔVRES_%rel_{y_new}-{y_old}"]     = rel_pct(delta[f"VRES_kWh_{y_new}"],     delta[f"VRES_kWh_{y_old}"])
    delta[f"ΔTotal_%rel_{y_new}-{y_old}"]    = rel_pct(delta[f"Total_kWh_{y_new}"],    delta[f"Total_kWh_{y_old}"])
    delta[f"ΔTotalREN_%rel_{y_new}-{y_old}"] = rel_pct(delta[f"TotalREN_kWh_{y_new}"], delta[f"TotalREN_kWh_{y_old}"])
    delta.replace([np.inf, -np.inf], np.nan, inplace=True)

    delta.to_csv(outfile, index=False)
    dprint(f"[SALVATO] {outfile}")

# Crea i tre delta
make_delta(detail_df, "2035", "2030", OUT_DELTA_35_30)
make_delta(detail_df, "2040", "2035", OUT_DELTA_40_35)
make_delta(detail_df, "2040", "2030", OUT_DELTA_40_30)

# === 1) UNICO GRAFICO: 2030 vs 2035 vs 2040 affiancati (metrica su TOTALE) ===
storage_order = ["N", "B", "P"]
group_order   = ["VRES", "VRES+GT"]

bar_width = 0.22
gap       = 1.2

x_positions = []
x_labels    = []
PV_2030, W_2030, PV_2035, W_2035, PV_2040, W_2040 = [], [], [], [], [], []
x = 0.0
for g in group_order:
    for s in storage_order:
        pv30 = data2030[(g, s)]["pv_pct_tot"]; w30  = data2030[(g, s)]["wind_pct_tot"]
        pv35 = data2035[(g, s)]["pv_pct_tot"]; w35  = data2035[(g, s)]["wind_pct_tot"]
        pv40 = data2040[(g, s)]["pv_pct_tot"]; w40  = data2040[(g, s)]["wind_pct_tot"]
        x_positions.append(x)
        x_labels.append(f"{g}\n{s}")
        PV_2030.append(pv30); W_2030.append(w30)
        PV_2035.append(pv35); W_2035.append(w35)
        PV_2040.append(pv40); W_2040.append(w40)
        x += gap

fig, ax = plt.subplots(figsize=(14, 6))

# 2030
ax.bar([p - bar_width for p in x_positions], W_2030, width=bar_width, label="Wind 2030", color=WIND_30)
ax.bar([p - bar_width for p in x_positions], PV_2030, bottom=W_2030, width=bar_width, label="PV 2030", color=PV_30)
# 2035
ax.bar([p for p in x_positions], W_2035, width=bar_width, label="Wind 2035", color=WIND_35)
ax.bar([p for p in x_positions], PV_2035, bottom=W_2035, width=bar_width, label="PV 2035", color=PV_35)
# 2040
ax.bar([p + bar_width for p in x_positions], W_2040, width=bar_width, label="Wind 2040", color=WIND_40)
ax.bar([p + bar_width for p in x_positions], PV_2040, bottom=W_2040, width=bar_width, label="PV 2040", color=PV_40)

ax.set_xticks(x_positions)
ax.set_xticklabels(x_labels)
ax.set_ylabel("VRES production [%] (su totale)")
max_y = max(PV_2030 + W_2030 + PV_2035 + W_2035 + PV_2040 + W_2040) if x_positions else 0
ax.set_ylim(0, max(100, 1.2 * max_y if max_y > 0 else 1))
ax.set_title("exisitng: % VRES (2030 vs 2035 vs 2040) – metrica su totale")
ax.legend(ncol=3, frameon=True)

plt.tight_layout()
plt.savefig(OUT_COMBINED, dpi=300, bbox_inches="tight")
plt.close(fig)
dprint(f"[SALVATO] {OUT_COMBINED}")

# === 2) GRAFICI “STACCATI”: 3 subplot (metrica su TOTALE) ===================
fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)

def plot_year(ax, year: str, dat: dict, wind_color: str, pv_color: str):
    bar_w = 0.6
    gap_g = 0.8
    x_pos, x_labs, tick_centers = [], [], []
    PV_vals, W_vals = [], []
    xloc = 0.0
    for g in group_order:
        for s in storage_order:
            PV_vals.append(dat[(g, s)]["pv_pct_tot"])
            W_vals.append(dat[(g, s)]["wind_pct_tot"])
            x_pos.append(xloc); x_labs.append(s); xloc += 1.0
        tick_centers.append(xloc - 1.5)
        xloc += gap_g

    ax.bar(x_pos, W_vals, width=bar_w, color=wind_color, label="Wind")
    ax.bar(x_pos, PV_vals, bottom=W_vals, width=bar_w, color=pv_color, label="PV")
    top_here = max((p + w) for p, w in zip(PV_vals, W_vals)) if PV_vals else 0.0

    ax.set_title(year, fontsize=14, fontweight="bold")
    ax.set_xticks([])
    for xx, lbl in zip(x_pos, x_labs):
        ax.text(xx, -2.5, lbl, ha="center", va="top", fontsize=9, clip_on=False)

    ax.text(tick_centers[0], 1.02, "VRES",
            transform=ax.get_xaxis_transform(), ha="center", va="bottom",
            fontsize=12, fontweight="bold")
    ax.text(tick_centers[1], 1.02, "VRES+GT",
            transform=ax.get_xaxis_transform(), ha="center", va="bottom",
            fontsize=12, fontweight="bold")
    return top_here

m1 = plot_year(axes[0], "2030", data2030, WIND_30, PV_30)
m2 = plot_year(axes[1], "2035", data2035, WIND_35, PV_35)
m3 = plot_year(axes[2], "2040", data2040, WIND_40, PV_40)
max_top = max(m1, m2, m3)

for ax in axes:
    ax.set_ylim(0, max(100, 1.2 * max_top if max_top > 0 else 1))
axes[0].set_ylabel("VRES production [%] (su totale)")

# legenda sinistra
leg_left = axes[0].legend(loc="upper left", frameon=True, fancybox=False, framealpha=1)
edge_col = leg_left.get_frame().get_edgecolor()
edge_lw  = leg_left.get_frame().get_linewidth()

# box N/B/P sulla destra
axes[2].text(
    0.98, 0.85, "N = NoStorage\nB = BESS\nP = PHES",
    transform=axes[2].transAxes, ha="right", va="top",
    bbox=dict(boxstyle="square,pad=0.3", fc="white", ec=edge_col, lw=edge_lw)
)

fig.suptitle("existing: % VRES – metrica su totale", fontsize=20, fontweight="bold", y=0.98)
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(OUT_SPLIT, dpi=300, bbox_inches="tight")
plt.close(fig)
dprint(f"[SALVATO] {OUT_SPLIT}")
