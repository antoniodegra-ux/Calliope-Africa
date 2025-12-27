# -*- coding: utf-8 -*-
"""
Thesis-ready Dispatch Plot with Demand Curve – Final version (PHES)
Continuous stacked area with harmonized palette, refined PHES visualization,
and demand curve (summed from regional timeseries).
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy.interpolate import PchipInterpolator
from pathlib import Path

# ========= CONFIG =========
SELECTED_DAY = "2040-12-03"
SELECTED_COUNTRY = "Eritrea"

BASE_DIR = Path("/Users/antoniodegrazia/Desktop/run_2040_new_true/run_autarky/")
PROD_FILE = BASE_DIR / "autarky_VRES_2040_PHES/results/results_carrier_prod.csv"
CON_FILE  = BASE_DIR / "autarky_VRES_2040_PHES/results/results_carrier_con.csv"
DEMAND_FILE = BASE_DIR / "autarky_VRES_2040_PHES/Timeseries/Demand.csv"

# ========= FONT & STYLE =========
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 12,
    "axes.labelsize": 13,
    "axes.titlesize": 15,
    "legend.fontsize": 11,
    "lines.linewidth": 1.2
})

# ========= 1) LOAD DATA =========
df_prod = pd.read_csv(PROD_FILE, usecols=["timesteps", "locs", "techs", "carrier_prod"])
df_con  = pd.read_csv(CON_FILE,  usecols=["timesteps", "locs", "techs", "carrier_con"])

# ========= 2) COUNTRY NORMALIZATION =========
def normalize_country(loc):
    if loc.startswith("Egypt"): return "Egypt"
    elif loc.startswith("KEN"): return "Kenya"
    elif loc.startswith("DRC"): return "DRC"
    elif loc.startswith("TAN"): return "Tanzania"
    elif loc.startswith("Eri"): return "Eritrea"
    elif loc.startswith("Eth"): return "Ethiopia"
    else: return loc

for df in [df_prod, df_con]:
    df["country"] = df["locs"].apply(normalize_country)
    df["time"] = pd.to_datetime(df["timesteps"])

# ========= 3) FILTER COUNTRY & DAY =========
sel_day = pd.to_datetime(SELECTED_DAY).date()
df_prod = df_prod[(df_prod["country"] == SELECTED_COUNTRY) & (df_prod["time"].dt.date == sel_day)]
df_con  = df_con[(df_con["country"] == SELECTED_COUNTRY) & (df_con["time"].dt.date == sel_day)]

# ========= 4) MAP CATEGORY =========
def map_category(tech):
    t = tech.lower()
    if "solar" in t or "pv" in t: return "Solar"
    elif "wind" in t: return "Wind"
    elif "hydro" in t and "phes" not in t: return "Hydro"
    elif "geo" in t: return "Geothermal"
    elif "bio" in t: return "Bioenergy"
    elif any(x in t for x in ["ocgt","ccgt","diesel","hfo","steam_turbine","gas_engine"]): return "Fossil"
    elif "phes" in t: return "PHES"
    else: return "Other"

df_prod["category"] = df_prod["techs"].apply(map_category)
df_con["category"]  = df_con["techs"].apply(map_category)

# ========= 5) PHES NET POWER =========
phes_prod = df_prod[df_prod["category"] == "PHES"].groupby("time")["carrier_prod"].sum()
phes_con  = df_con[df_con["category"] == "PHES"].groupby("time")["carrier_con"].sum()
phes_net  = (phes_prod + phes_con).fillna(0)

# ========= 6) REMOVE PHES FROM MAIN MIX =========
df_prod = df_prod[df_prod["category"] != "PHES"]

# ========= 7) AGGREGATE OTHER TECHS =========
df_prod["hour"] = df_prod["time"].dt.hour
dispatch_day = df_prod.groupby(["hour","category"])["carrier_prod"].sum().unstack(fill_value=0)
dispatch_day_gwh = dispatch_day / 1_000_000.0

# ========= 8) PHES GWh BY HOUR =========
phes_hour = phes_net.groupby(phes_net.index.hour).sum() / 1_000_000.0
phes_hour = phes_hour.reindex(range(24), fill_value=0)

# ========= 9) INTERPOLATION =========
hours = np.arange(24)
smooth_hours = np.linspace(0, 23, 241)
smoothed = pd.DataFrame(index=smooth_hours)
for col in dispatch_day_gwh.columns:
    f = PchipInterpolator(hours, dispatch_day_gwh[col].values)
    smoothed[col] = f(smooth_hours)

f_phes = PchipInterpolator(hours, phes_hour.values)
phes_interp = f_phes(smooth_hours)

# ========= 10) LOAD & PROCESS DEMAND =========
df_dem = pd.read_csv(DEMAND_FILE)
df_dem.rename(columns={df_dem.columns[0]: "time"}, inplace=True)
df_dem["time"] = pd.to_datetime(df_dem["time"], format="%Y/%m/%d %H:%M:%S")

# Somma delle regioni del paese selezionato
country_cols = [c for c in df_dem.columns if c.startswith(SELECTED_COUNTRY)]
demand_nat = -df_dem[country_cols].sum(axis=1)  # valori positivi
demand_df = pd.DataFrame({"time": df_dem["time"], "demand_GWh": demand_nat / 1_000_000.0})

# Filtra giorno
demand_df = demand_df[demand_df["time"].dt.date == sel_day]
demand_df["hour"] = demand_df["time"].dt.hour
demand_hour = demand_df.groupby("hour")["demand_GWh"].sum()
demand_hour = demand_hour.reindex(range(24), fill_value=0)

# Interpola la curva di domanda
f_dem = PchipInterpolator(hours, demand_hour.values)
demand_interp = f_dem(smooth_hours)

# ========= 11) COLORS =========
COLORS = {
    "Fossil": "#8c564b",
    "Wind": "#b0c9ff",
    "Hydro": "#1f77b4",
    "Solar": "#ffd700",
    "Geothermal": "#ff7f0e",
    "Bioenergy": "#2ca02c",
    "Other": "#d3d3d3"
}
desired_order = ["Fossil","Hydro","Other","Wind","Solar","Geothermal","Bioenergy"]
cols_ordered = [c for c in desired_order if c in smoothed.columns]
cat_colors = [COLORS.get(c,"#d3d3d3") for c in cols_ordered]

# ========= 12) SHARES =========
shares = (dispatch_day_gwh.sum() / dispatch_day_gwh.sum().sum() * 100).round(1)
shares = shares[cols_ordered]

# ========= 13) PLOT =========
fig, ax = plt.subplots(figsize=(11,5.5))
smoothed[cols_ordered].plot.area(ax=ax, color=cat_colors, alpha=0.9, linewidth=0, legend=False)

total_gen = smoothed.sum(axis=1)

# --- PHES pumping (charging) ---
ax.fill_between(smooth_hours, total_gen - np.clip(-phes_interp, 0, None), total_gen,
                where=phes_interp < 0, facecolor="#b3e6b3", alpha=0.3,
                hatch="////", edgecolor="#006600", linewidth=0.5, label="PHES pumping")

# --- PHES generating (discharging) ---
ax.fill_between(smooth_hours, total_gen, total_gen + np.clip(phes_interp, 0, None),
                where=phes_interp > 0, facecolor="#009900", alpha=0.3,
                hatch="\\\\\\\\", edgecolor="#004d00", linewidth=0.5, label="PHES generating")

# --- Demand curve ---
ax.plot(smooth_hours, demand_interp, color="black", linewidth=2.5, label="Demand")

# ========= 14) LABELS =========
ax.set_xlim(0,23)
ax.set_xticks(range(0,24,3))
ax.set_xlabel("Hour of the day", fontsize=13)
ax.set_ylabel(r"$\mathbf{Power\ [GW]}$", fontsize=13, fontweight="bold")
ax.tick_params(axis='both', labelsize=11)
ax.spines[['top','right']].set_visible(False)
ax.set_ylim(0, 0.3)  # 🔹 scala fissa per coerenza

# ========= 15) LEGEND =========
handles = [Patch(facecolor=COLORS.get(cat,"#d3d3d3")) for cat in cols_ordered]
legend_labels = [f"{cat}: {shares[cat]:.1f}%" for cat in cols_ordered]
handles += [
    Patch(facecolor="#b3e6b3", alpha=0.3, hatch="////", edgecolor="#006600", label="PHES pumping"),
    Patch(facecolor="#009900", alpha=0.3, hatch="\\\\\\\\", edgecolor="#004d00", label="PHES generating"),
    plt.Line2D([0],[0], color="black", linewidth=2.5, label="Demand")
]
legend_labels += ["PHES pumping", "PHES generating", "Demand"]

ax.legend(handles, legend_labels, title="Technologies", fontsize=10.5, title_fontsize=12,
          loc="center left", bbox_to_anchor=(1.02, 0.5),
          framealpha=0.9, facecolor="white", edgecolor="black")

ax.set_title(f"Daily Dispatch — {SELECTED_COUNTRY}, {SELECTED_DAY}", fontsize=15, pad=10, fontweight="bold")
fig.tight_layout(rect=[0, 0, 0.87, 1])

# ========= 16) SAVE =========
scenario_name = PROD_FILE.parts[-3]
out_path = PROD_FILE.parent / f"{scenario_name}_{SELECTED_COUNTRY}_{SELECTED_DAY}_dispatch_PHES_wDemand_thesis_final.png"
fig.savefig(out_path, dpi=400, bbox_inches="tight")
plt.close(fig)

print(f"✅ Figure saved to: {out_path}")
