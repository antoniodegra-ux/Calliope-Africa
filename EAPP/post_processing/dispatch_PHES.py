# -*- coding: utf-8 -*-
"""
Thesis-ready Dispatch Plot – Final version (PHES)
Continuous stacked area with harmonized palette, refined PHES visualization,
and legend with % shares (only for generation technologies).
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
    else: return loc

for df in [df_prod, df_con]:
    df["country"] = df["locs"].apply(normalize_country)
    df["time"] = pd.to_datetime(df["timesteps"])

# ========= 3) FILTER COUNTRY & DAY =========
df_prod = df_prod[(df_prod["country"] == SELECTED_COUNTRY) &
                  (df_prod["time"].dt.date == pd.to_datetime(SELECTED_DAY).date())]
df_con  = df_con[(df_con["country"] == SELECTED_COUNTRY) &
                 (df_con["time"].dt.date == pd.to_datetime(SELECTED_DAY).date())]

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
# Include anche PHES_2035_installed, PHES_2040_installed, ecc.
phes_prod = df_prod[df_prod["techs"].str.contains("PHES", case=False, na=False)].groupby("time")["carrier_prod"].sum()
phes_con  = df_con[df_con["techs"].str.contains("PHES", case=False, na=False)].groupby("time")["carrier_con"].sum()
phes_net  = (phes_prod + phes_con).fillna(0)    # + generation, - pumping

# ========= 6) REMOVE PHES FROM MAIN MIX =========
df_prod = df_prod[~df_prod["techs"].str.contains("PHES", case=False, na=False)]

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

# ========= 10) COLORS =========
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

# ========= 11) CALCULATE SHARES =========
shares = (dispatch_day_gwh.sum() / dispatch_day_gwh.sum().sum() * 100).round(1)
shares = shares[cols_ordered]

# ========= 12) PLOT =========
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

# ========= 13) LABELS =========
ax.set_xlim(0,23)
ax.set_xticks(range(0,24,3))
ax.set_xlabel("Hour of the day", fontsize=13)
ax.set_ylabel("Energy [GWh]", fontsize=13)
ax.tick_params(axis='both', labelsize=11)
ax.spines[['top','right']].set_visible(False)
ax.set_ylim(0, None)

# ========= 14) LEGEND =========
handles = [Patch(facecolor=COLORS.get(cat,"#d3d3d3")) for cat in cols_ordered]
legend_labels = [f"{cat}: {shares[cat]:.1f}%" for cat in cols_ordered]
# PHES senza percentuali
handles += [
    Patch(facecolor="#b3e6b3", alpha=0.3, hatch="////", edgecolor="#006600", label="PHES pumping"),
    Patch(facecolor="#009900", alpha=0.3, hatch="\\\\\\\\", edgecolor="#004d00", label="PHES generating")
]
legend_labels += ["PHES pumping", "PHES generating"]

# 👉 Legend positioned outside (right)
ax.legend(handles, legend_labels, title="Technologies", fontsize=10.5, title_fontsize=12,
          loc="center left", bbox_to_anchor=(1.02, 0.5),
          framealpha=0.9, facecolor="white", edgecolor="none")

ax.set_title(f"Daily Dispatch — {SELECTED_COUNTRY}, {SELECTED_DAY}", fontsize=15, pad=10)
fig.tight_layout(rect=[0, 0, 0.87, 1])  # leave room for legend

# ========= 15) SAVE =========
scenario_name = PROD_FILE.parts[-3]
out_path = PROD_FILE.parent / f"{scenario_name}_{SELECTED_COUNTRY}_{SELECTED_DAY}_dispatch_PHES_thesis_final.png"
fig.savefig(out_path, dpi=400, bbox_inches="tight")
plt.close(fig)

print(f"✅ Figure saved to: {out_path}")
