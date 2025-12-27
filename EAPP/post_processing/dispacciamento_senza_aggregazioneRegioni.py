# -*- coding: utf-8 -*-
"""
Thesis-ready Dispatch Plot – Final version
Continuous stacked area with harmonized palette, refined BESS visualization,
and legend with % shares (only for generation technologies).
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy.interpolate import PchipInterpolator
from pathlib import Path

# ========= CONFIG =========
SELECTED_DAY = "2040-07-03"
SELECTED_COUNTRY = "Egypt_UE"

BASE_DIR = Path("/Users/antoniodegrazia/Desktop/run_2040_new_true/run_autarky/")
PROD_FILE = BASE_DIR / "autarky_VRES_2040_nostorage/results/results_carrier_prod.csv"
CON_FILE  = BASE_DIR / "autarky_VRES_2040_nostorage/results/results_carrier_con.csv"

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

# ========= 2) FILTER COUNTRY & DAY =========
df_prod = df_prod[(df_prod["locs"] == SELECTED_COUNTRY) &
                  (df_prod["timesteps"].str[:10] == SELECTED_DAY)]
df_con  = df_con[(df_con["locs"] == SELECTED_COUNTRY) &
                 (df_con["timesteps"].str[:10] == SELECTED_DAY)]

# ========= 3) MAP CATEGORY =========
def map_category(tech):
    t = tech.lower()
    if "solar" in t or "pv" in t: return "Solar"
    elif "wind" in t: return "Wind"
    elif "hydro" in t: return "Hydro"
    elif "geo" in t: return "Geothermal"
    elif "bio" in t: return "Bioenergy"
    elif any(x in t for x in ["ocgt","ccgt","diesel","hfo","steam_turbine","gas_engine"]): return "Fossil"
    elif "bess" in t: return "BESS"
    else: return "Other"

df_prod["category"] = df_prod["techs"].apply(map_category)
df_con["category"]  = df_con["techs"].apply(map_category)

# ========= 4) BESS NET POWER =========
bess_prod = df_prod[df_prod["category"] == "BESS"].groupby("timesteps")["carrier_prod"].sum()
bess_con  = df_con[df_con["category"] == "BESS"].groupby("timesteps")["carrier_con"].sum()
bess_net  = (bess_prod + bess_con).fillna(0)    # + discharge, - charge

# ========= 5) REMOVE BESS FROM MAIN MIX =========
df_prod = df_prod[df_prod["category"] != "BESS"]

# ========= 6) AGGREGATE OTHER TECHS BY HOUR =========
df_prod["hour"] = pd.to_datetime(df_prod["timesteps"]).dt.hour
dispatch_day = df_prod.groupby(["hour", "category"])["carrier_prod"].sum().unstack(fill_value=0)
dispatch_day_gwh = dispatch_day / 1_000_000.0

# ========= 7) BESS GWh BY HOUR =========
# Assicurati che l'indice di bess_net sia un DatetimeIndex
bess_net.index = pd.to_datetime(bess_net.index)

# Ora puoi usare .hour
bess_hour = bess_net.groupby(bess_net.index.hour).sum() / 1_000_000.0
bess_hour = bess_hour.reindex(range(24), fill_value=0)

# ========= 8) INTERPOLATION =========
hours = np.arange(24)
smooth_hours = np.linspace(0, 23, 241)
smoothed = pd.DataFrame(index=smooth_hours)
for col in dispatch_day_gwh.columns:
    f = PchipInterpolator(hours, dispatch_day_gwh[col].values)
    smoothed[col] = f(smooth_hours)

f_bess = PchipInterpolator(hours, bess_hour.values)
bess_interp = f_bess(smooth_hours)

# ========= 9) COLORS =========
COLORS = {
    "Fossil": "#8c564b",
    "Wind": "#b0c9ff",
    "Hydro": "#1f77b4",
    "Solar": "#ffd700",
    "Geothermal": "#ff7f0e",
    "Bioenergy": "#2ca02c",
    "Other": "#d3d3d3"
}
desired_order = ["Fossil", "Bioenergy", "Geothermal", "Other", "Hydro", "Wind", "Solar"]
cols_ordered = [c for c in desired_order if c in smoothed.columns]
cat_colors = [COLORS.get(c, "#d3d3d3") for c in cols_ordered]

# ========= 10) CALCULATE SHARES =========
shares = (dispatch_day_gwh.sum() / dispatch_day_gwh.sum().sum() * 100).round(1)
shares = shares[cols_ordered]

# ========= 11) HANDLE MISSING DATA =========
# Check for NaN values and handle them
smoothed[cols_ordered] = smoothed[cols_ordered].apply(pd.to_numeric, errors='coerce')
smoothed = smoothed.fillna(0)  # Fill NaNs with 0

# ========= 12) PLOT =========
fig, ax = plt.subplots(figsize=(11, 5.5))
smoothed[cols_ordered].plot.area(ax=ax, color=cat_colors, alpha=0.9, linewidth=0, legend=False)

total_gen = smoothed.sum(axis=1)

# --- BESS charging (light red, hatched) ---
ax.fill_between(smooth_hours, total_gen - np.clip(-bess_interp, 0, None), total_gen,
                where=bess_interp < 0, facecolor="#ffb3b3", alpha=0.3,
                hatch="////", edgecolor="#990000", linewidth=0.5, label="BESS charging")

# --- BESS discharging (dark red, opposite hatch) ---
ax.fill_between(smooth_hours, total_gen, total_gen + np.clip(bess_interp, 0, None),
                where=bess_interp > 0, facecolor="#cc0000", alpha=0.3,
                hatch="\\\\\\\\", edgecolor="#660000", linewidth=0.5, label="BESS discharging")

# ========= 13) LABELS =========
ax.set_xlim(0, 23)
ax.set_xticks(range(0, 24, 3))
ax.set_xlabel("Hour of the day", fontsize=13)
ax.set_ylabel("Energy [GWh]", fontsize=13)
ax.tick_params(axis='both', labelsize=11)
ax.spines[['top', 'right']].set_visible(False)
ax.set_ylim(0, 40)

# ========= 14) LEGEND (boxed, thin border) =========
handles = [Patch(facecolor=COLORS.get(cat, "#d3d3d3")) for cat in cols_ordered]
legend_labels = [f"{cat}: {shares[cat]:.1f}%" for cat in cols_ordered]
handles += [
    Patch(facecolor="#ffb3b3", alpha=0.3, hatch="////", edgecolor="#990000", label="BESS charging"),
    Patch(facecolor="#cc0000", alpha=0.3, hatch="\\\\\\\\", edgecolor="#660000", label="BESS discharging")
]
legend_labels += ["BESS charging", "BESS discharging"]

legend = ax.legend(
    handles, legend_labels,
    title="Technologies", fontsize=10.5, title_fontsize=12,
    loc="center left", bbox_to_anchor=(1.02, 0.5),
    framealpha=0.9, facecolor="white", edgecolor="black"
)
legend.get_frame().set_linewidth(0.8)  # ✅ bordo sottile

ax.set_title(f"Daily Dispatch — {SELECTED_COUNTRY}, {SELECTED_DAY}", fontsize=15, pad=10)
fig.tight_layout(rect=[0, 0, 0.87, 1])  # leave room for legend

# ========= 15) SAVE =========
scenario_name = PROD_FILE.parts[-3]
out_path = PROD_FILE.parent / f"{scenario_name}_{SELECTED_COUNTRY}_{SELECTED_DAY}_dispatch_nostorage_thesis_final.png"
fig.savefig(out_path, dpi=400, bbox_inches="tight")
plt.close(fig)

print(f"✅ Figure saved to: {out_path}")
